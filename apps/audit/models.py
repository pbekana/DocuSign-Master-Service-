"""Audit and logging models."""
from django.db import models


class AuditLog(models.Model):
    """Operational and security event logging."""
    
    EVENT_TYPES = [
        ('AUTH_SUCCESS', 'Authentication Success'),
        ('AUTH_FAILURE', 'Authentication Failure'),
        ('HMAC_VALIDATION_SUCCESS', 'HMAC Validation Success'),
        ('HMAC_VALIDATION_FAILURE', 'HMAC Validation Failure'),
        ('NONCE_REPLAY_DETECTED', 'Nonce Replay Detected'),
        ('JOB_CREATED', 'Job Created'),
        ('JOB_STATUS_CHANGED', 'Job Status Changed'),
        ('JOB_CANCELLED', 'Job Cancelled'),
        ('JOB_RESUMED', 'Job Resumed'),
        ('EXTRACTION_STARTED', 'Extraction Started'),
        ('EXTRACTION_COMPLETED', 'Extraction Completed'),
        ('EXTRACTION_FAILED', 'Extraction Failed'),
        ('RATE_LIMIT_DETECTED', 'Rate Limit Detected'),
        ('RETRY_EXHAUSTED', 'Retry Exhausted'),
        ('NORMALIZATION_STARTED', 'Normalization Started'),
        ('NORMALIZATION_COMPLETED', 'Normalization Completed'),
        ('MINIO_UPLOAD_STARTED', 'MinIO Upload Started'),
        ('MINIO_UPLOAD_COMPLETED', 'MinIO Upload Completed'),
        ('MINIO_UPLOAD_FAILED', 'MinIO Upload Failed'),
        ('JOB_REMOVED', 'Job Removed'),
        ('MAINTENANCE_CLEANUP', 'Maintenance Cleanup'),
        ('CRASH_DETECTED', 'Crash Detected'),
    ]
    
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    organization_id = models.CharField(max_length=255, db_index=True, blank=True)
    client_id = models.CharField(max_length=255, blank=True)
    job_id = models.CharField(max_length=255, db_index=True, blank=True)
    outcome = models.CharField(max_length=50, blank=True)  # SUCCESS, FAILURE, etc.
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional event data")
    
    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['organization_id', 'timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"


class FailedExternalCall(models.Model):
    """Track external operations that failed after retries exhausted."""
    
    STATUS_CHOICES = [
        ('PENDING_RETRY', 'Pending Retry'),
        ('RETRY_EXHAUSTED', 'Retry Exhausted'),
        ('RESOLVED', 'Resolved'),
    ]
    
    service = models.CharField(max_length=100)  # docusign, minio, etc.
    operation = models.CharField(max_length=255)  # get_envelopes, upload_file, etc.
    job_id = models.CharField(max_length=255, db_index=True, blank=True)
    organization_id = models.CharField(max_length=255, db_index=True, blank=True)
    request_metadata = models.JSONField(default=dict, help_text="Sanitized request info")
    attempts = models.IntegerField(default=0)
    last_error = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING_RETRY')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['service', 'created_at']),
            models.Index(fields=['status', 'updated_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.service}.{self.operation} - {self.status}"


class OutputMetadata(models.Model):
    """Track generated output files and their locations."""
    
    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('parquet', 'Parquet'),
    ]
    
    job_id = models.CharField(max_length=255, db_index=True)
    organization_id = models.CharField(max_length=255, db_index=True)
    table_name = models.CharField(max_length=100)  # envelopes, recipients, etc.
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES)
    row_count = models.IntegerField(default=0)
    local_path = models.CharField(max_length=500, blank=True)
    minio_key = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['job_id', 'table_name']),
            models.Index(fields=['organization_id', 'created_at']),
        ]
        unique_together = ['job_id', 'table_name', 'format']
    
    def __str__(self):
        return f"{self.job_id[:8]}.../{self.table_name}.{self.format}"
