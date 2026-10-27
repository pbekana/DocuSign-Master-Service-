"""Common views for health and statistics."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from apps.jobs.models import Job
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """Health check endpoint (public, no authentication required)."""
    
    def get(self, request):
        """Check service health."""
        try:
            # Check database connection
            connection.ensure_connection()
            
            return Response({
                'status': 'healthy',
                'service': 'DocuSign Master Service',
                'database': 'connected'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return Response({
                'status': 'unhealthy',
                'error': str(e)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class StatsView(APIView):
    """Service statistics endpoint (public, no authentication required)."""
    
    def get(self, request):
        """Get service statistics."""
        try:
            total_jobs = Job.objects.count()
            jobs_by_status = {}
            
            for choice in Job.STATUS_CHOICES:
                status_key = choice[0]
                count = Job.objects.filter(status=status_key).count()
                jobs_by_status[status_key] = count
            
            total_audit_events = AuditLog.objects.count()
            
            return Response({
                'total_jobs': total_jobs,
                'jobs_by_status': jobs_by_status,
                'total_audit_events': total_audit_events,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
