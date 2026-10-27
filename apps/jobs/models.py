"""Job management models for DocuSign extraction."""
import uuid
from django.db import models
from django.utils import timezone


class Job(models.Model):
    """Main extraction job record."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('FETCHING_ENVELOPES', 'Fetching Envelopes'),
        ('FETCHING_DETAILS', 'Fetching Details'),
        ('NORMALIZING', 'Normalizing'),
        ('UPLOADING_TO_MINIO', 'Uploading to MinIO'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('CRASHED', 'Crashed'),
    ]
    
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_id = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    stage = models.CharField(max_length=100, default='')
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    extraction_config = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Progress tracking
    progress = models.JSONField(default=dict, help_text="Progress info: current_stage, items_processed")
    record_counts = models.JSONField(default=dict, help_text="Counts by record type: envelopes, recipients, documents, templates")
    error_details = models.TextField(default='', blank=True)
    
    # Normalization and storage status
    normalization_status = models.CharField(max_length=50, default='PENDING')
    minio_upload_status = models.CharField(max_length=50, default='PENDING')
    output_metadata_summary = models.JSONField(default=dict)
    
    class Meta:
        indexes = [
            models.Index(fields=['organization_id', 'created_at']),
            models.Index(fields=['status', 'last_heartbeat']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Job {self.job_id} - {self.status}"


class JobCheckpoint(models.Model):
    """Checkpoint for job recovery and resumption."""
    
    STAGE_CHOICES = [
        ('FETCHING_ENVELOPES', 'Fetching Envelopes'),
        ('FETCHING_RECIPIENTS', 'Fetching Recipients'),
        ('FETCHING_DOCUMENTS', 'Fetching Documents'),
        ('FETCHING_TEMPLATES', 'Fetching Templates'),
        ('NORMALIZATION', 'Normalization'),
        ('MINIO_UPLOAD', 'MinIO Upload'),
    ]
    
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='latest_checkpoint')
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES)
    page_position = models.IntegerField(default=0)
    records_processed = models.IntegerField(default=0)
    last_envelope_id = models.CharField(max_length=255, default='', blank=True)
    last_document_id = models.CharField(max_length=255, default='', blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['job', 'timestamp']),
        ]
    
    def __str__(self):
        return f"Checkpoint for Job {self.job_id} - {self.stage}"


class NonceStore(models.Model):
    """Track nonces for HMAC replay protection."""
    
    nonce = models.CharField(max_length=255, unique=True, db_index=True)
    client_id = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Nonce {self.nonce[:8]}... for {self.client_id}"
