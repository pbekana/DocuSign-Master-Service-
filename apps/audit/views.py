"""Views for audit and logging endpoints."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


class AuditLogsView(APIView):
    """Retrieve audit logs."""
    
    def get(self, request):
        """Get audit logs with pagination and filtering."""
        try:
            organization_id = request.query_params.get('organization_id')
            event_type = request.query_params.get('event_type')
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
            
            queryset = AuditLog.objects.all()
            
            if organization_id:
                queryset = queryset.filter(organization_id=organization_id)
            
            if event_type:
                queryset = queryset.filter(event_type=event_type)
            
            total = queryset.count()
            logs = queryset[offset:offset + limit]
            
            return Response({
                'logs': [
                    {
                        'event_type': log.event_type,
                        'organization_id': log.organization_id,
                        'client_id': log.client_id,
                        'job_id': log.job_id,
                        'outcome': log.outcome,
                        'timestamp': log.timestamp.isoformat(),
                        'metadata': log.metadata,
                    }
                    for log in logs
                ],
                'total': total,
                'limit': limit,
                'offset': offset,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuditStatsView(APIView):
    """Get audit statistics."""
    
    def get(self, request):
        """Get audit event statistics."""
        try:
            organization_id = request.query_params.get('organization_id')
            
            queryset = AuditLog.objects.all()
            
            if organization_id:
                queryset = queryset.filter(organization_id=organization_id)
            
            stats = {
                'total_events': queryset.count(),
                'by_event_type': {},
            }
            
            for choice in AuditLog.EVENT_TYPES:
                event_type = choice[0]
                count = queryset.filter(event_type=event_type).count()
                if count > 0:
                    stats['by_event_type'][event_type] = count
            
            return Response(stats, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting audit statistics: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
