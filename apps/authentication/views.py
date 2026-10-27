"""Views for authentication endpoints."""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.authentication.services import DocuSignAuthService

logger = logging.getLogger(__name__)


class ValidateCredentialsView(APIView):
    """Validate DocuSign credentials endpoint."""
    
    def post(self, request):
        """Validate provided credentials."""
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
