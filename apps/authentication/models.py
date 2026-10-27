"""
Authentication-related models including nonce storage for replay protection.
"""
from django.db import models


class NonceStore(models.Model):
    """Stores used nonces for HMAC replay protection."""
    
    nonce = models.CharField(max_length=255, unique=True, db_index=True)
    client_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Nonce {self.nonce} for {self.client_id}"
