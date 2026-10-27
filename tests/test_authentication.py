"""
Tests for HMAC authentication middleware.
"""
import pytest
import hmac
import hashlib
import time
from django.test import RequestFactory, override_settings
from apps.authentication.middleware import HMACAuthenticationMiddleware, compute_signature
from apps.jobs.models import NonceStore


@pytest.mark.django_db
class TestHMACAuth:
    """Test HMAC authentication middleware."""
    
    @override_settings(HMAC_ENABLED=False)
    def test_hmac_disabled(self):
        """Test that HMAC can be disabled."""
        factory = RequestFactory()
        request = factory.post('/api/scan/start', data={})
        
        def get_response(r):
            return None
        
        middleware = HMACAuthenticationMiddleware(get_response)
        response = middleware(request)
        
        # Should pass through when HMAC is disabled
        assert response is None
    
    @override_settings(HMAC_ENABLED=True, HMAC_SECRET_KEY_CORE='test-secret', HMAC_SECRET_KEY_ENGINEER='engineer-secret', HMAC_SIGNATURE_MAX_AGE=300)
    def test_missing_headers(self):
        """Test rejection when HMAC headers are missing."""
        factory = RequestFactory()
        request = factory.post('/api/scan/start', data={})
        
        def get_response(r):
            return None
        
        middleware = HMACAuthenticationMiddleware(get_response)
        response = middleware(request)
        
        # Should return 401 response
        assert response is not None
        assert response.status_code == 401
    
    @override_settings(
        HMAC_ENABLED=True,
        HMAC_SECRET_KEY_CORE='test-secret',
        HMAC_SECRET_KEY_ENGINEER='engineer-secret',
        HMAC_SIGNATURE_MAX_AGE=300
    )
    def test_valid_signature_coordinator(self):
        """Test successful authentication with valid signature from coordinator."""
        factory = RequestFactory()
        
        # Create request data
        body = b''
        timestamp = str(int(time.time()))
        nonce = 'test-nonce-12345'
        client_id = 'coordinator'
        
        # Calculate signature using the same method as middleware
        signature = compute_signature(
            'POST',
            '/api/scan/start',
            timestamp,
            nonce,
            body,
            'test-secret'
        )
        
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
        
        def get_response(r):
            return None
        
        middleware = HMACAuthenticationMiddleware(get_response)
        response = middleware(request)
        
        # Should pass authentication
        assert response is None
        assert hasattr(request, 'client_id')
        assert request.client_id == client_id
    
    @override_settings(
        HMAC_ENABLED=True,
        HMAC_SECRET_KEY_CORE='test-secret',
        HMAC_SECRET_KEY_ENGINEER='engineer-secret',
        HMAC_SIGNATURE_MAX_AGE=300
    )
    def test_nonce_replay_protection(self):
        """Test that nonces cannot be reused."""
        # Store a nonce
        NonceStore.objects.create(nonce='used-nonce', client_id='coordinator')
        
        factory = RequestFactory()
        timestamp = str(int(time.time()))
        
        request = factory.post(
            '/api/scan/start',
            HTTP_X_DS_SIGNATURE='dummy',
            HTTP_X_DS_TIMESTAMP=timestamp,
            HTTP_X_DS_CLIENT_ID='coordinator',
            HTTP_X_DS_NONCE='used-nonce'
        )
        
        def get_response(r):
            return None
        
        middleware = HMACAuthenticationMiddleware(get_response)
        response = middleware(request)
        
        # Should be rejected
        assert response is not None
        assert response.status_code == 401
