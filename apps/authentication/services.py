"""DocuSign authentication services."""
import logging
import time
import requests
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)


class DocuSignAuthService:
    """Handle DocuSign authentication and token management."""
    
    def __init__(self):
        self.integration_key = settings.DOCUSIGN_INTEGRATION_KEY
        self.user_id = settings.DOCUSIGN_USER_ID
        self.private_key_path = settings.DOCUSIGN_PRIVATE_KEY_PATH
        self.oauth_host = settings.DOCUSIGN_AUTH_SERVER
        self.scopes = ['signature', 'impersonation']
        self.timeout = settings.DOCUSIGN_REQUEST_TIMEOUT
        self.token_cache = {}
    
    def _load_private_key(self):
        """Load RSA private key from file."""
        try:
            with open(self.private_key_path, 'r') as f:
                key_content = f.read()
            private_key = serialization.load_pem_private_key(
                key_content.encode(),
                password=None,
                backend=default_backend()
            )
            return private_key
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise
    
    def get_access_token_jwt(self):
        """Get access token using JWT Grant flow (server-to-server)."""
        cache_key = 'docusign_jwt_token'
        
        # Check cache
        if cache_key in self.token_cache:
            token_data = self.token_cache[cache_key]
            if datetime.utcnow() < token_data['expiry']:
                return token_data['token']
        
        # Generate JWT
        private_key = self._load_private_key()
        now = datetime.utcnow()
        payload = {
            'iss': self.integration_key,
            'sub': self.user_id,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(hours=1)).timestamp()),
            'aud': self.oauth_host,
            'scope': ' '.join(self.scopes)
        }
        
        assertion = jwt.encode(payload, private_key, algorithm='RS256')
        
        # Request token
        token_url = f"{self.oauth_host}/oauth/token"
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=self.timeout)
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            
            # Cache token
            self.token_cache[cache_key] = {
                'token': access_token,
                'expiry': datetime.utcnow() + timedelta(seconds=expires_in - 60)  # Refresh 60s before expiry
            }
            
            logger.info("Successfully obtained JWT access token")
            return access_token
        except Exception as e:
            logger.error(f"Failed to get JWT token: {e}")
            raise
    
    def resolve_account_base_url(self, access_token):
        """Get account ID and base URL from user info endpoint."""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Call user info endpoint to get account info
            userinfo_url = f"{self.oauth_host}/oauth/userinfo"
            response = requests.get(userinfo_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            user_info = response.json()
            
            # Extract account info
            if 'accounts' not in user_info or not user_info['accounts']:
                raise ValueError("No DocuSign accounts found in userinfo response")
            
            # Get the first account (primary)
            account = user_info['accounts'][0]
            account_id = account['account_id']
            base_url = account['base_uri']
            
            logger.info(f"Resolved account {account_id} with base URL {base_url}")
            return account_id, base_url
        except Exception as e:
            logger.error(f"Failed to resolve account base URL: {e}")
            raise
    
    def validate_credentials(self, credentials):
        """Validate provided credentials without creating a job."""
        try:
            # If it's a JWT flow, we just need to verify we can get a token
            token = self.get_access_token_jwt()
            account_id, base_url = self.resolve_account_base_url(token)
            
            return {
                'valid': True,
                'account_id': account_id,
                'base_url': base_url,
                'message': 'Credentials are valid'
            }
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'message': 'Credentials are invalid or DocuSign is unreachable'
            }
