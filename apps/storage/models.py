"""Storage service models."""
from django.db import models


class StorageLog(models.Model):
    """Log storage operations."""
    job_id = models.CharField(max_length=255, db_index=True)
    operation = models.CharField(max_length=100)  # upload, download, delete
    storage_size_bytes = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
