"""
DocuSign API client for extraction operations.
"""
import time
import random
import requests
from django.conf import settings
from apps.audit.models import AuditLog
from apps.resilience.models import FailedExternalCall


class ExtractionError(Exception):
    """Raised when extraction operations fail."""
    pass


class DocuSignClient:
    """Client for DocuSign eSignature REST API v2.1."""
    
    def __init__(self, access_token, account_id, base_url):
        """
        Initialize DocuSign client.
        
        Args:
            access_token: OAuth access token
            account_id: DocuSign account ID
            base_url: Account-specific base URL
        """
        self.access_token = access_token
        self.account_id = account_id
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        })
    
    def get_envelopes(self, start_date, end_date, start_position=0, count=100):
        """
        Fetch envelopes within date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            start_position: Pagination start position
            count: Number of records per page
        
        Returns:
            dict: Response with envelopes, resultSetSize, totalSetSize, nextUri
        """
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes"
        params = {
            'from_date': start_date,
            'to_date': end_date,
            'start_position': start_position,
            'count': count
        }
        
        return self._make_request('GET', url, params=params, operation='get_envelopes')
    
    def get_envelope_recipients(self, envelope_id):
        """
        Fetch recipients for an envelope.
        
        Args:
            envelope_id: Envelope ID
        
        Returns:
            dict: Recipients data
        """
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/recipients"
        return self._make_request('GET', url, operation='get_envelope_recipients')
    
    def get_envelope_documents(self, envelope_id):
        """
        Fetch document metadata for an envelope (no binary content).
        
        Args:
            envelope_id: Envelope ID
        
        Returns:
            dict: Document metadata
        """
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/envelopes/{envelope_id}/documents"
        return self._make_request('GET', url, operation='get_envelope_documents')
    
    def get_templates(self, start_position=0, count=100):
        """
        Fetch templates with pagination.
        
        Args:
            start_position: Pagination start position
            count: Number of records per page
        
        Returns:
            dict: Response with templates
        """
        url = f"{self.base_url}/v2.1/accounts/{self.account_id}/templates"
        params = {
            'start_position': start_position,
            'count': count
        }
        
        return self._make_request('GET', url, params=params, operation='get_templates')
    
    def _make_request(self, method, url, params=None, data=None, operation='api_call', attempt=1):
        """
        Make HTTP request with rate limiting and retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            data: Request body
            operation: Operation name for logging
            attempt: Current retry attempt
        
        Returns:
            dict: Response JSON
        """
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=data,
                timeout=settings.DOCUSIGN_REQUEST_TIMEOUT
            )
            
            # Handle rate limiting (HTTP 429)
            if response.status_code == 429:
                retry_after = self._parse_retry_after(response.headers.get('Retry-After', '60'))
                
                AuditLog.objects.create(
                    event_type='RATE_LIMIT_HIT',
                    outcome='SUCCESS',
                    metadata={
                        'operation': operation,
                        'retry_after': retry_after,
                        'attempt': attempt
                    }
                )
                
                if attempt <= settings.DOCUSIGN_MAX_RETRIES:
                    time.sleep(retry_after)
                    return self._make_request(method, url, params, data, operation, attempt + 1)
                else:
                    raise ExtractionError(f'Rate limit exceeded after {attempt} attempts')
            
            # Handle retryable errors
            if response.status_code in [500, 502, 503, 504]:
                if attempt <= settings.DOCUSIGN_MAX_RETRIES:
                    delay = self._calculate_backoff(attempt)
                    time.sleep(delay)
                    return self._make_request(method, url, params, data, operation, attempt + 1)
                else:
                    self._record_failed_call(operation, url, response.status_code, response.text)
                    raise ExtractionError(
                        f'Request failed after {attempt} attempts: {response.status_code}'
                    )
            
            # Handle other errors
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            if attempt <= settings.DOCUSIGN_MAX_RETRIES:
                delay = self._calculate_backoff(attempt)
                time.sleep(delay)
                return self._make_request(method, url, params, data, operation, attempt + 1)
            else:
                self._record_failed_call(operation, url, 'TIMEOUT', 'Request timeout')
                raise ExtractionError(f'Request timeout after {attempt} attempts')
        
        except requests.exceptions.RequestException as e:
            self._record_failed_call(operation, url, 'ERROR', str(e))
            raise ExtractionError(f'Request failed: {e}')
    
    def _parse_retry_after(self, retry_after):
        """Parse Retry-After header (integer seconds or HTTP date)."""
        try:
            return int(retry_after)
        except ValueError:
            # Could be HTTP date format, default to 60 seconds
            return 60
    
    def _calculate_backoff(self, attempt):
        """Calculate exponential backoff with jitter."""
        base_delay = 2 ** attempt  # Exponential: 2, 4, 8, 16...
        jitter = random.uniform(0, 1)
        return base_delay + jitter
    
    def _record_failed_call(self, operation, url, status, error_message):
        """Record failed external call after retry exhaustion."""
        FailedExternalCall.objects.create(
            target_service='DOCUSIGN',
            operation=operation,
            request_metadata={
                'url': url,
                'status': str(status)
            },
            attempts=settings.DOCUSIGN_MAX_RETRIES,
            last_error=error_message,
            failure_status='ACTIVE'
        )
