"""
DocuSign authentication service for JWT Grant and Authorization Code Grant.
"""
import time
import jwt
import requests
from pathlib import Path
from django.conf import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class DocuSignAuthService:
    """Handles DocuSign OAuth authentication."""
    
    # Token cache: {credentials_hash: (token, expiry_time)}
    _token_cache = {}
    
    @classmethod
    def get_access_token(cls, credentials):
        """
        Get access token using JWT Grant or from cache.
        
        Args:
            credentials: dict with integration_key, user_id, private_key_path, auth_server
        
        Returns:
            str: Access token
        """
        # Check cache
        cache_key = cls._hash_credentials(credentials)
        if cache_key in cls._token_cache:
            token, expiry = cls._token_cache[cache_key]
            if time.time() < expiry - 60:  # 60 second buffer
                return token
        
        # Generate new token using JWT Grant
        token, expires_in = cls._get_access_token_jwt(
            credentials.get('integration_key') or settings.DOCUSIGN_INTEGRATION_KEY,
            credentials.get('user_id') or settings.DOCUSIGN_USER_ID,
            credentials.get('private_key_path') or settings.DOCUSIGN_PRIVATE_KEY_PATH,
            credentials.get('auth_server') or settings.DOCUSIGN_AUTH_SERVER,
            credentials.get('scopes') or settings.DOCUSIGN_OAUTH_SCOPES
        )
        
        # Cache token
        cls._token_cache[cache_key] = (token, time.time() + expires_in)
        
        return token
    
    @classmethod
    def _get_access_token_jwt(cls, integration_key, user_id, private_key_path, auth_server, scopes):
        """
        Obtain access token using JWT Grant flow.
        
        Returns:
            tuple: (access_token, expires_in)
        """
        # Load private key
        private_key_path = Path(private_key_path).expanduser()
        with open(private_key_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend()
            )
        
        # Create JWT
        now = int(time.time())
        jwt_payload = {
            'iss': integration_key,
            'sub': user_id,
            'aud': auth_server,
            'iat': now,
            'exp': now + 3600,
            'scope': scopes
        }
        
        assertion = jwt.encode(jwt_payload, private_key, algorithm='RS256')
        
        # Request access token
        token_url = f'https://{auth_server}/oauth/token'
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': assertion
        }
        
        response = requests.post(
            token_url,
            data=data,
            timeout=settings.DOCUSIGN_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        token_data = response.json()
        return token_data['access_token'], token_data.get('expires_in', 3600)
    
    @classmethod
    def resolve_account_base_url(cls, access_token, auth_server=None):
        """
        Resolve account ID and base URL using /oauth/userinfo endpoint.
        
        Returns:
            tuple: (account_id, base_url)
        """
        auth_server = auth_server or settings.DOCUSIGN_AUTH_SERVER
        userinfo_url = f'https://{auth_server}/oauth/userinfo'
        
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            userinfo_url,
            headers=headers,
            timeout=settings.DOCUSIGN_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        user_info = response.json()
        accounts = user_info.get('accounts', [])
        
        if not accounts:
            raise ValueError('No DocuSign accounts found for this user')
        
        # Use first account
        account = accounts[0]
        account_id = account['account_id']
        base_uri = account['base_uri']
        
        # Construct full base URL
        base_url = f"{base_uri}/restapi"
        
        return account_id, base_url
    
    @classmethod
    def validate_credentials(cls, credentials):
        """
        Validate DocuSign credentials by attempting authentication.
        
        Args:
            credentials: dict with integration_key, user_id, private_key_path, auth_server
        
        Returns:
            dict: {valid: bool, account_id: str, base_url: str, error: str}
        """
        try:
            access_token = cls.get_access_token(credentials)
            account_id, base_url = cls.resolve_account_base_url(
                access_token,
                credentials.get('auth_server')
            )
            
            return {
                'valid': True,
                'account_id': account_id,
                'base_url': base_url,
                'error': None
            }
        except Exception as e:
            return {
                'valid': False,
                'account_id': None,
                'base_url': None,
                'error': str(e)
            }
    
    @classmethod
    def _hash_credentials(cls, credentials):
        """Generate cache key from credentials."""
        import hashlib
        key_string = f"{credentials.get('integration_key')}_{credentials.get('user_id')}"
        return hashlib.md5(key_string.encode()).hexdigest()
