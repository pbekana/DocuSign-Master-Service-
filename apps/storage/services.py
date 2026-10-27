"""
MinIO storage service for uploading normalized outputs.
"""
from minio import Minio
from minio.error import S3Error
from django.conf import settings
from pathlib import Path
from apps.storage.models import OutputMetadata
from apps.resilience.models import FailedExternalCall


class MinIOStorageService:
    """Manages MinIO uploads for job outputs."""
    
    def __init__(self, job):
        """
        Initialize MinIO storage service.
        
        Args:
            job: Job model instance
        """
        self.job = job
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            # Bucket might exist but access denied, or other error
            pass
    
    def upload_all_files(self):
        """Upload all normalized files to MinIO."""
        # Get all output metadata records for this job that haven't been uploaded
        output_files = OutputMetadata.objects.filter(
            job=self.job,
            format='PARQUET',  # Only upload Parquet files
            minio_key__exact=''
        )
        
        for output_file in output_files:
            self._upload_file(output_file)
    
    def _upload_file(self, output_metadata):
        """
        Upload a single file to MinIO with retry logic.
        
        Args:
            output_metadata: OutputMetadata instance
        """
        local_path = Path(output_metadata.local_path)
        if not local_path.exists():
            return
        
        # Construct MinIO key with required pattern
        # docusign/{table_name}/glynac_organization_id={org_id}/processing_date={date}/{table}.parquet
        processing_date = self.job.created_at.strftime('%Y-%m-%d')
        object_key = (
            f"docusign/{output_metadata.table_name}/"
            f"glynac_organization_id={self.job.organization_id}/"
            f"processing_date={processing_date}/"
            f"{output_metadata.table_name}.parquet"
        )
        
        # Retry upload
        for attempt in range(1, settings.MINIO_MAX_RETRIES + 1):
            try:
                self.client.fput_object(
                    self.bucket,
                    object_key,
                    str(local_path)
                )
                
                # Update metadata on success
                output_metadata.minio_key = object_key
                output_metadata.save()
                
                return
                
            except Exception as e:
                if attempt >= settings.MINIO_MAX_RETRIES:
                    # Record failure
                    FailedExternalCall.objects.create(
                        target_service='MINIO',
                        operation='upload_file',
                        job_id=str(self.job.job_id),
                        organization_id=self.job.organization_id,
                        request_metadata={
                            'bucket': self.bucket,
                            'key': object_key,
                            'local_path': str(local_path)
                        },
                        attempts=settings.MINIO_MAX_RETRIES,
                        last_error=str(e),
                        failure_status='ACTIVE'
                    )
                    raise
                # Wait before retry (simple linear backoff)
                import time
                time.sleep(attempt * 2)
