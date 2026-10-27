"""Resilience service models."""
from django.db import models


class RetryLog(models.Model):
    """Log retry attempts."""
    job_id = models.CharField(max_length=255, db_index=True)
    operation = models.CharField(max_length=255)
    attempt_number = models.IntegerField(default=1)
    error_message = models.TextField()
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
