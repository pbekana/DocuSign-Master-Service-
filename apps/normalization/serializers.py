"""
Serializers for normalization endpoints.
"""
from rest_framework import serializers
from apps.storage.models import OutputMetadata


class OutputMetadataSerializer(serializers.ModelSerializer):
    """Serializer for OutputMetadata model."""
    
    class Meta:
        model = OutputMetadata
        fields = ['table_name', 'format', 'row_count', 'local_path', 'minio_key', 'created_at']
