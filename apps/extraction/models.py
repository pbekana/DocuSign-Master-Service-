"""Extraction service models."""
from django.db import models


class ExtractionLog(models.Model):
    """Log extraction operations for debugging."""
    job_id = models.CharField(max_length=255, db_index=True)
    record_type = models.CharField(max_length=100)  # envelopes, recipients, etc.
    records_extracted = models.IntegerField(default=0)
    extraction_time_seconds = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
