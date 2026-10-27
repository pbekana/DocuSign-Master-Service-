"""HMAC authentication middleware for DocuSign Master Service."""
import hashlib
import hmac
import time
from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import sync_and_async_middleware
from apps.jobs.models import NonceStore
from apps.audit.models import AuditLog


def compute_signature(method, path, timestamp, nonce, body, secret):
    """Compute HMAC-SHA256 signature for request."""
    canonical_request = f"{method}\n{path}\n{timestamp}\n{nonce}\n{hashlib.sha256(body).hexdigest()}"
    signature = hmac.new(
        secret.encode(),
        canonical_request.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def constant_time_compare(a, b):
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(a, b)


@sync_and_async_middleware
def HMACAuthenticationMiddleware(get_response):
    """Middleware for HMAC signature validation."""
    
    # Routes that don't require HMAC authentication
    public_routes = ['/api/health', '/api/stats', '/admin/']
    
    def middleware(request):
        # Check if this route requires authentication
        path = request.path
        requires_auth = not any(path.startswith(route) for route in public_routes)
        
        if requires_auth and settings.HMAC_ENABLED:
            # Extract HMAC headers
            signature = request.headers.get('X-DS-Signature', '')
            timestamp_str = request.headers.get('X-DS-Timestamp', '')
            client_id = request.headers.get('X-DS-Client-ID', '')
            nonce = request.headers.get('X-DS-Nonce', '')
            
            # Validate headers presence
            if not all([signature, timestamp_str, client_id, nonce]):
                AuditLog.objects.create(
                    event_type='HMAC_VALIDATION_FAILURE',
                    client_id=client_id or 'unknown',
                    outcome='MISSING_HEADERS',
                    metadata={'headers_present': bool(signature and timestamp_str and client_id and nonce)}
                )
                return JsonResponse({'error': 'Missing HMAC headers'}, status=401)
            
            # Validate timestamp (not older than max age)
            try:
                request_time = int(float(timestamp_str))
                current_time = int(time.time())
                if abs(current_time - request_time) > settings.HMAC_SIGNATURE_MAX_AGE:
                    AuditLog.objects.create(
                        event_type='HMAC_VALIDATION_FAILURE',
                        client_id=client_id,
                        outcome='TIMESTAMP_EXPIRED',
                    )
                    return JsonResponse({'error': 'Request timestamp expired'}, status=401)
            except ValueError:
                return JsonResponse({'error': 'Invalid timestamp'}, status=401)
            
            # Check nonce for replay protection
            if NonceStore.objects.filter(nonce=nonce).exists():
                AuditLog.objects.create(
                    event_type='NONCE_REPLAY_DETECTED',
                    client_id=client_id,
                    outcome='REPLAY',
                )
                return JsonResponse({'error': 'Nonce already used'}, status=401)
            
            # Determine which secret to use based on client_id (this maps to permissions)
            if client_id == 'coordinator':
                secret = settings.HMAC_SECRET_KEY_CORE
                permission_level = 'write'
            elif client_id == 'engineer':
                secret = settings.HMAC_SECRET_KEY_ENGINEER
                permission_level = 'read-only'
            else:
                AuditLog.objects.create(
                    event_type='HMAC_VALIDATION_FAILURE',
                    client_id=client_id,
                    outcome='UNKNOWN_CLIENT',
                )
                return JsonResponse({'error': 'Unknown client ID'}, status=401)
            
            # Validate signature
            body = request.body if request.body else b''
            expected_signature = compute_signature(
                request.method,
                request.path,
                timestamp_str,
                nonce,
                body,
                secret
            )
            
            if not constant_time_compare(signature, expected_signature):
                AuditLog.objects.create(
                    event_type='HMAC_VALIDATION_FAILURE',
                    client_id=client_id,
                    outcome='INVALID_SIGNATURE',
                )
                return JsonResponse({'error': 'Invalid signature'}, status=401)
            
            # Store nonce to prevent replay
            NonceStore.objects.create(nonce=nonce, client_id=client_id)
            
            # Log successful validation
            AuditLog.objects.create(
                event_type='HMAC_VALIDATION_SUCCESS',
                client_id=client_id,
                outcome='SUCCESS',
            )
            
            # Attach authentication info to request
            request.hmac_authenticated = True
            request.client_id = client_id
            request.permission_level = permission_level
            
            # Enforce read-only for engineer key on write operations
            if permission_level == 'read-only' and request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                return JsonResponse({'error': 'Engineer key cannot perform write operations'}, status=403)
        
        response = get_response(request)
        return response
    
    return middleware
