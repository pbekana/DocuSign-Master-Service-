"""Maintenance and operational views."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from apps.jobs.models import Job, JobCheckpoint, NonceStore
from apps.jobs.services import JobService
from apps.audit.models import AuditLog, OutputMetadata

logger = logging.getLogger(__name__)


class MaintenanceCleanupView(APIView):
    """Clean up old jobs and associated data."""
    
    def post(self, request):
        """Perform maintenance cleanup."""
        try:
            retention_days = settings.RETENTION_DAYS
            cutoff_date = timezone.now() - timedelta(days=retention_days)
            
            # Delete old completed jobs and their associated data
            old_jobs = Job.objects.filter(
                status__in=['COMPLETED', 'FAILED', 'CANCELLED'],
                completed_at__lt=cutoff_date
            )
            
            job_count = old_jobs.count()
            job_ids = list(old_jobs.values_list('job_id', flat=True))
            
            # Delete checkpoints
            JobCheckpoint.objects.filter(job__job_id__in=job_ids).delete()
            
            # Delete output metadata
            OutputMetadata.objects.filter(job_id__in=[str(jid) for jid in job_ids]).delete()
            
            # Delete jobs
            old_jobs.delete()
            
            # Clean up old nonces (older than 24 hours)
            nonce_cutoff = timezone.now() - timedelta(hours=24)
            old_nonces = NonceStore.objects.filter(created_at__lt=nonce_cutoff)
            nonce_count = old_nonces.count()
            old_nonces.delete()
            
            # Log cleanup event
            AuditLog.objects.create(
                event_type='MAINTENANCE_CLEANUP',
                outcome='SUCCESS',
                metadata={
                    'jobs_deleted': job_count,
                    'nonces_deleted': nonce_count,
                    'retention_days': retention_days,
                }
            )
            
            logger.info(f"Maintenance cleanup: deleted {job_count} jobs and {nonce_count} nonces")
            
            return Response({
                'message': 'Cleanup completed',
                'jobs_deleted': job_count,
                'nonces_deleted': nonce_count,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during maintenance cleanup: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DetectCrashedView(APIView):
    """Detect and mark jobs that appear to have crashed."""
    
    def post(self, request):
        """Detect crashed jobs."""
        try:
            count = JobService.detect_crashed_jobs()
            
            return Response({
                'message': f'Detected and marked {count} crashed jobs',
                'crashed_jobs_count': count,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error detecting crashed jobs: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
