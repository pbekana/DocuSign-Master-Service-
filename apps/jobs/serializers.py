"""
Serializers for job management endpoints.
"""
from rest_framework import serializers
from apps.jobs.models import Job
from datetime import date


class JobSerializer(serializers.ModelSerializer):
    """Serializer for Job model."""
    
    class Meta:
        model = Job
        fields = [
            'job_id', 'organization_id', 'status', 'date_from', 'date_to',
            'extraction_config', 'current_stage', 'created_at', 'started_at',
            'completed_at', 'last_heartbeat', 'progress', 'record_counts',
            'error_details', 'normalization_status', 'minio_upload_status',
            'output_metadata', 'worker_id'
        ]
        read_only_fields = [
            'job_id', 'status', 'created_at', 'started_at', 'completed_at',
            'last_heartbeat', 'progress', 'record_counts', 'error_details',
            'normalization_status', 'minio_upload_status', 'output_metadata',
            'worker_id'
        ]


class CreateJobSerializer(serializers.Serializer):
    """Serializer for creating a new job."""
    
    organization_id = serializers.CharField(max_length=255)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    extraction_config = serializers.JSONField(required=False, default=dict)
    
    def validate(self, data):
        """Validate date range."""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        if date_to < date_from:
            raise serializers.ValidationError('date_to must be >= date_from')
        
        # Check range not too large (max 365 days)
        delta = (date_to - date_from).days
        if delta > 365:
            raise serializers.ValidationError('Date range cannot exceed 365 days')
        
        return data


class JobStatusSerializer(serializers.ModelSerializer):
    """Lightweight serializer for job status."""
    
    class Meta:
        model = Job
        fields = [
            'job_id', 'organization_id', 'status', 'current_stage',
            'created_at', 'started_at', 'completed_at', 'progress',
            'record_counts', 'error_details'
        ]
