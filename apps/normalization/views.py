"""Views for normalization endpoints."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.jobs.models import Job
from apps.audit.models import OutputMetadata

logger = logging.getLogger(__name__)


class NormalizeScanView(APIView):
    """Trigger normalization for a completed extraction scan."""
    
    def post(self, request, scan_id):
        """Start normalization of extracted data."""
        try:
            job = Job.objects.get(job_id=scan_id)
            
            if job.status != 'COMPLETED':
                return Response(
                    {'error': f'Can only normalize COMPLETED jobs, job is in {job.status} state'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update normalization status to in progress
            job.normalization_status = 'IN_PROGRESS'
            job.save()
            
            return Response({
                'scan_id': str(job.job_id),
                'normalization_status': 'IN_PROGRESS',
                'message': 'Normalization queued'
            }, status=status.HTTP_202_ACCEPTED)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error starting normalization: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListTablesView(APIView):
    """List normalized tables for a scan."""
    
    def get(self, request, scan_id):
        """Get list of generated tables/outputs."""
        try:
            job = Job.objects.get(job_id=scan_id)
            
            tables = OutputMetadata.objects.filter(job_id=str(scan_id))
            
            return Response({
                'scan_id': str(job.job_id),
                'tables': [
                    {
                        'table_name': t.table_name,
                        'format': t.format,
                        'row_count': t.row_count,
                        'local_path': t.local_path,
                        'minio_key': t.minio_key,
                        'created_at': t.created_at.isoformat(),
                        'uploaded_at': t.uploaded_at.isoformat() if t.uploaded_at else None,
                    }
                    for t in tables
                ]
            }, status=status.HTTP_200_OK)
        except Job.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


class SupportedObjectsView(APIView):
    """Get list of supported extraction object types."""
    
    def get(self, request):
        """Return supported extraction objects."""
        return Response({
            'supported_objects': [
                'envelopes',
                'recipients',
                'documents',
                'templates'
            ]
        }, status=status.HTTP_200_OK)
