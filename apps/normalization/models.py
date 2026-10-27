"""Normalization service models."""
from django.db import models


class NormalizationLog(models.Model):
    """Log normalization operations."""
    job_id = models.CharField(max_length=255, db_index=True)
    table_name = models.CharField(max_length=100)
    normalization_time_seconds = models.FloatField(default=0)
    input_rows = models.IntegerField(default=0)
    output_rows = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
