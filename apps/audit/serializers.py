"""
Serializers for audit endpoints.
"""
from rest_framework import serializers
from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'event_type', 'organization_id', 'client_id',
            'outcome', 'timestamp', 'metadata', 'job_id'
        ]
