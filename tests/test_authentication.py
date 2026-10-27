"""
Tests for HMAC authentication middleware.
"""
import pytest
import hmac
import hashlib
import time
from django.test import RequestFactory
from apps.authentication.middleware import HMACAuthMiddleware
from apps.authentication.models import NonceStore


@pytest.mark.django_db
class TestHMACAuth:
    """Test HMAC authentication middleware."""
    
    def test_public_endpoint_bypassed(self):
        """Test that public endpoints bypass authentication."""
        factory = RequestFactory()
        request = factory.get('/api/health')
        
        middleware = HMACAuthMiddleware(lambda r: None)
        response = middleware.process_request(request)
        
        # None means continue processing (not rejected)
        assert response is None
    
    def test_missing_headers(self):
        """Test rejection when HMAC headers are missing."""
        factory = RequestFactory()
        request = factory.post('/api/scan/start', data={})
        
        middleware = HMACAuthMiddleware(lambda r: None)
        response = middleware.process_request(request)
        
        # Should return 401 response
        assert response is not None
        assert response.status_code == 401
    
    def test_valid_signature(self):
        """Test successful authentication with valid signature."""
        factory = RequestFactory()
        
        # Create request data
        body = '{"test": "data"}'
        timestamp = str(int(time.time()))
        nonce = 'test-nonce-12345'
        client_id = 'COORDINATOR'
        
        # Calculate signature
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        canonical = f"POST\n/api/scan/start\n{timestamp}\n{nonce}\n{body_hash}"
        secret = 'test-secret'
        signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        
        # Create request with headers
        request = factory.post(
            '/api/scan/start',
            data=body,
            content_type='application/json',
            HTTP_X_DS_SIGNATURE=signature,
            HTTP_X_DS_TIMESTAMP=timestamp,
            HTTP_X_DS_CLIENT_ID=client_id,
            HTTP_X_DS_NONCE=nonce
        )
        
        # Mock settings
        from django.conf import settings
        settings.HMAC_SECRET_KEY_COORDINATOR = secret
        settings.HMAC_ENABLED = True
        settings.HMAC_MAX_AGE_SECONDS = 300
        
        middleware = HMACAuthMiddleware(lambda r: None)
        response = middleware.process_request(request)
        
        # Should pass authentication
        assert response is None
        assert hasattr(request, 'hmac_client_id')
        assert request.hmac_client_id == client_id
    
    def test_nonce_replay_protection(self):
        """Test that nonces cannot be reused."""
        # Store a nonce
        NonceStore.objects.create(nonce='used-nonce', client_id='COORDINATOR')
        
        factory = RequestFactory()
        timestamp = str(int(time.time()))
        
        request = factory.post(
            '/api/scan/start',
            HTTP_X_DS_SIGNATURE='dummy',
            HTTP_X_DS_TIMESTAMP=timestamp,
            HTTP_X_DS_CLIENT_ID='COORDINATOR',
            HTTP_X_DS_NONCE='used-nonce'
        )
        
        from django.conf import settings
        settings.HMAC_ENABLED = True
        
        middleware = HMACAuthMiddleware(lambda r: None)
        response = middleware.process_request(request)
        
        # Should be rejected
        assert response is not None
        assert response.status_code == 401
