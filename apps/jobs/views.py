"""REST API views for job management."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
from apps.jobs.models import Job
from apps.jobs.services import JobService, CheckpointService
from apps.authentication.services import DocuSignAuthService
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


class StartScanView(APIView):
    """Start a new extraction scan/job."""
    
    def post(self, request):
        """Create and queue a new extraction job."""
        try:
            data = request.data
            organization_id = data.get('organization_id')
            date_from_str = data.get('date_from')  # ISO format
            date_to_str = data.get('date_to')
            extraction_config = data.get('extraction_config', {})
            
            # Validate required fields
            if not all([organization_id, date_from_str, date_to_str]):
                return Response(
                    {'error': 'Missing required fields: organization_id, date_from, date_to'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse dates
            try:
                date_from = timezone.datetime.fromisoformat(date_from_str.replace('Z', '+00:00'))
                date_to = timezone.datetime.fromisoformat(date_to_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return Response(
                    {'error': 'Invalid date format. Use ISO 8601 format.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate date range
            if date_from >= date_to:
                return Response(
                    {'error': 'date_from must be before date_to'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create job
            job = JobService.create_job(
                organization_id=organization_id,
                date_from=date_from,
                date_to=date_to,
                extraction_config=extraction_config,
                created_by=getattr(request, 'client_id', 'api')
            )
            
            return Response(
                {
                    'scan_id': str(job.job_id),
                    'status': job.status,
                    'message': 'Job queued for processing'
                },
                status=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            logger.error(f"Error starting scan: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScanStatusView(APIView):
    """Get the status of a specific scan/job."""
    
    def get(self, request, scan_id):
        """Retrieve job status details."""
        try:
            job = JobService.get_job_status(scan_id)
            
            return Response({
                'scan_id': str(job.job_id),
                'status': job.status,
                'stage': job.stage,
                'organization_id': job.organization_id,
                'date_from': job.date_from.isoformat(),
                'date_to': job.date_to.isoformat(),
                'created_at': job.created_at.isoformat(),
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'progress': job.progress,
                'record_counts': job.record_counts,
                'error_details': job.error_details,
                'normalization_status': job.normalization_status,
                'minio_upload_status': job.minio_upload_status,
            }, status=status.HTTP_200_OK)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


class CancelScanView(APIView):
    """Cancel an ongoing extraction scan/job."""
    
    def post(self, request, scan_id):
        """Cancel a job."""
        try:
            job = JobService.cancel_job(scan_id)
            
            return Response({
                'scan_id': str(job.job_id),
                'status': job.status,
                'message': 'Job cancelled'
            }, status=status.HTTP_200_OK)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResumeScanView(APIView):
    """Resume a failed or crashed extraction scan/job."""
    
    def post(self, request, scan_id):
        """Resume a job from checkpoint."""
        try:
            if not CheckpointService.can_resume(scan_id):
                return Response(
                    {'error': 'Job cannot be resumed (not in FAILED or CRASHED state or no checkpoint)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            job, checkpoint = CheckpointService.resume_job(scan_id)
            
            return Response({
                'scan_id': str(job.job_id),
                'status': job.status,
                'message': 'Job resumed from checkpoint',
                'checkpoint': {
                    'stage': checkpoint.stage,
                    'page_position': checkpoint.page_position,
                    'records_processed': checkpoint.records_processed,
                }
            }, status=status.HTTP_200_OK)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ListScansView(APIView):
    """List extraction scans/jobs with optional filtering."""
    
    def get(self, request):
        """List jobs."""
        try:
            organization_id = request.query_params.get('organization_id')
            status_filter = request.query_params.get('status')
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
            
            jobs, total = JobService.list_jobs(
                organization_id=organization_id,
                status=status_filter,
                limit=limit,
                offset=offset
            )
            
            return Response({
                'jobs': [
                    {
                        'scan_id': str(job.job_id),
                        'status': job.status,
                        'organization_id': job.organization_id,
                        'created_at': job.created_at.isoformat(),
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'record_counts': job.record_counts,
                    }
                    for job in jobs
                ],
                'total': total,
                'limit': limit,
                'offset': offset,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error listing scans: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScanStatisticsView(APIView):
    """Get statistics about extraction scans."""
    
    def get(self, request):
        """Get job statistics."""
        try:
            organization_id = request.query_params.get('organization_id')
            
            queryset = Job.objects.all()
            if organization_id:
                queryset = queryset.filter(organization_id=organization_id)
            
            stats = {
                'total_jobs': queryset.count(),
                'by_status': {},
            }
            
            for choice in Job.STATUS_CHOICES:
                status_key = choice[0]
                count = queryset.filter(status=status_key).count()
                stats['by_status'][status_key] = count
            
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RemoveScanView(APIView):
    """Remove/delete a scan and its associated data."""
    
    def delete(self, request, scan_id):
        """Delete a job (only if completed or failed)."""
        try:
            job = Job.objects.get(job_id=scan_id)
            
            # Only allow deletion of completed or failed jobs
            if job.status not in ['COMPLETED', 'FAILED', 'CANCELLED']:
                return Response(
                    {'error': f'Cannot delete job in {job.status} state'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            org_id = job.organization_id
            job_id = str(job.job_id)
            
            job.delete()
            
            AuditLog.objects.create(
                event_type='JOB_REMOVED',
                organization_id=org_id,
                job_id=job_id,
                outcome='SUCCESS'
            )
            
            return Response({'message': 'Job removed'}, status=status.HTTP_200_OK)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


class ValidateCredentialsView(APIView):
    """Validate DocuSign credentials."""
    
    def post(self, request):
        """Validate credentials without creating a job."""
        try:
            auth_service = DocuSignAuthService()
            result = auth_service.validate_credentials(None)
            
            if result['valid']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            return Response(
                {'error': str(e), 'valid': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
