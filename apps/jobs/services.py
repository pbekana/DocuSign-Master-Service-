"""Job management services."""
import logging
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from apps.jobs.models import Job, JobCheckpoint
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


class JobService:
    """Service for job lifecycle management."""
    
    @staticmethod
    def create_job(organization_id, date_from, date_to, extraction_config=None, created_by=None):
        """Create a new extraction job."""
        extraction_config = extraction_config or {}
        
        job = Job.objects.create(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to,
            extraction_config=extraction_config,
            status='PENDING',
            progress={'current_stage': 'PENDING', 'items_processed': 0},
            record_counts={'envelopes': 0, 'recipients': 0, 'documents': 0, 'templates': 0}
        )
        
        # Log event
        AuditLog.objects.create(
            event_type='JOB_CREATED',
            organization_id=organization_id,
            job_id=str(job.job_id),
            outcome='SUCCESS',
            metadata={'date_from': date_from.isoformat(), 'date_to': date_to.isoformat()}
        )
        
        logger.info(f"Created job {job.job_id} for organization {organization_id}")
        return job
    
    @staticmethod
    def update_status(job_id, new_status, stage=None, error_details=None):
        """Update job status and optionally stage."""
        try:
            job = Job.objects.get(job_id=job_id)
            old_status = job.status
            
            # Validate state transition
            JobService._validate_state_transition(old_status, new_status)
            
            job.status = new_status
            if stage:
                job.stage = stage
            if error_details:
                job.error_details = error_details
            
            if new_status == 'COMPLETED':
                job.completed_at = timezone.now()
            elif new_status == 'FETCHING_ENVELOPES' and not job.started_at:
                job.started_at = timezone.now()
            
            job.save()
            
            # Log event
            AuditLog.objects.create(
                event_type='JOB_STATUS_CHANGED',
                organization_id=job.organization_id,
                job_id=str(job.job_id),
                outcome='SUCCESS',
                metadata={'old_status': old_status, 'new_status': new_status, 'stage': stage}
            )
            
            logger.info(f"Job {job_id} status changed: {old_status} → {new_status}")
            return job
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            raise
    
    @staticmethod
    def _validate_state_transition(old_status, new_status):
        """Validate that a state transition is allowed."""
        valid_transitions = {
            'PENDING': ['FETCHING_ENVELOPES', 'CANCELLED', 'FAILED'],
            'FETCHING_ENVELOPES': ['FETCHING_DETAILS', 'FAILED', 'CANCELLED', 'CRASHED'],
            'FETCHING_DETAILS': ['NORMALIZING', 'FAILED', 'CANCELLED', 'CRASHED'],
            'NORMALIZING': ['UPLOADING_TO_MINIO', 'FAILED', 'CANCELLED', 'CRASHED'],
            'UPLOADING_TO_MINIO': ['COMPLETED', 'FAILED', 'CANCELLED', 'CRASHED'],
            'COMPLETED': [],
            'FAILED': ['FETCHING_ENVELOPES'],  # Allow resume from checkpoint
            'CANCELLED': [],
            'CRASHED': ['FETCHING_ENVELOPES'],  # Allow resume from checkpoint
        }
        
        if new_status not in valid_transitions.get(old_status, []):
            raise ValueError(f"Invalid transition: {old_status} → {new_status}")
    
    @staticmethod
    def update_progress(job_id, progress_dict, record_counts_dict=None):
        """Update job progress and record counts."""
        try:
            job = Job.objects.get(job_id=job_id)
            job.progress = progress_dict
            if record_counts_dict:
                job.record_counts = record_counts_dict
            job.save()
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found for progress update")
    
    @staticmethod
    def update_heartbeat(job_id):
        """Update last heartbeat timestamp."""
        try:
            job = Job.objects.get(job_id=job_id)
            job.last_heartbeat = timezone.now()
            job.save(update_fields=['last_heartbeat'])
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found for heartbeat update")
    
    @staticmethod
    def cancel_job(job_id):
        """Cancel a job if it's in a cancellable state."""
        try:
            job = Job.objects.get(job_id=job_id)
            
            terminal_states = ['COMPLETED', 'FAILED', 'CANCELLED', 'CRASHED']
            if job.status in terminal_states:
                raise ValueError(f"Cannot cancel job in {job.status} state")
            
            job.status = 'CANCELLED'
            job.save()
            
            AuditLog.objects.create(
                event_type='JOB_CANCELLED',
                organization_id=job.organization_id,
                job_id=str(job.job_id),
                outcome='SUCCESS'
            )
            
            logger.info(f"Job {job_id} cancelled")
            return job
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            raise
    
    @staticmethod
    def get_job_status(job_id):
        """Retrieve full job status details."""
        try:
            return Job.objects.get(job_id=job_id)
        except Job.DoesNotExist:
            logger.error(f"Job {job_id} not found")
            raise
    
    @staticmethod
    def list_jobs(organization_id=None, status=None, limit=100, offset=0):
        """List jobs with optional filtering."""
        queryset = Job.objects.all()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        total = queryset.count()
        jobs = queryset[offset:offset + limit]
        
        return list(jobs), total
    
    @staticmethod
    def detect_crashed_jobs():
        """Find jobs that appear to have crashed (no heartbeat for too long)."""
        from django.utils.timezone import now
        from datetime import timedelta
        
        timeout_minutes = settings.HEARTBEAT_TIMEOUT_MINUTES
        threshold = now() - timedelta(minutes=timeout_minutes)
        
        active_states = ['FETCHING_ENVELOPES', 'FETCHING_DETAILS', 'NORMALIZING', 'UPLOADING_TO_MINIO']
        crashed_jobs = Job.objects.filter(
            status__in=active_states,
            last_heartbeat__lt=threshold
        )
        
        count = 0
        for job in crashed_jobs:
            job.status = 'CRASHED'
            job.save()
            
            AuditLog.objects.create(
                event_type='CRASH_DETECTED',
                organization_id=job.organization_id,
                job_id=str(job.job_id),
                outcome='SUCCESS',
                metadata={'last_heartbeat': job.last_heartbeat.isoformat()}
            )
            
            count += 1
        
        logger.info(f"Detected and marked {count} crashed jobs")
        return count


class CheckpointService:
    """Service for job checkpointing and recovery."""
    
    @staticmethod
    def save_checkpoint(job_id, stage, page_position=0, records_processed=0, last_envelope_id='', last_document_id=''):
        """Save or update a checkpoint for job recovery."""
        try:
            checkpoint, created = JobCheckpoint.objects.update_or_create(
                job_id=job_id,
                defaults={
                    'stage': stage,
                    'page_position': page_position,
                    'records_processed': records_processed,
                    'last_envelope_id': last_envelope_id,
                    'last_document_id': last_document_id,
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} checkpoint for job {job_id} at {stage}, position {page_position}")
            return checkpoint
        except Exception as e:
            logger.error(f"Failed to save checkpoint for job {job_id}: {e}")
            raise
    
    @staticmethod
    def get_latest_checkpoint(job_id):
        """Retrieve the latest checkpoint for a job."""
        try:
            return JobCheckpoint.objects.get(job_id=job_id)
        except JobCheckpoint.DoesNotExist:
            return None
    
    @staticmethod
    def can_resume(job_id):
        """Check if a job can be resumed from a checkpoint."""
        try:
            job = Job.objects.get(job_id=job_id)
            checkpoint = JobCheckpoint.objects.filter(job_id=job_id).exists()
            
            resumable_states = ['FAILED', 'CRASHED']
            return job.status in resumable_states and checkpoint
        except Job.DoesNotExist:
            return False
    
    @staticmethod
    def resume_job(job_id):
        """Resume a job from its latest checkpoint."""
        try:
            job = Job.objects.get(job_id=job_id)
            checkpoint = JobCheckpoint.objects.get(job_id=job_id)
            
            if not CheckpointService.can_resume(job_id):
                raise ValueError(f"Job {job_id} cannot be resumed")
            
            # Reset job to appropriate extraction stage
            job.status = 'FETCHING_ENVELOPES'
            job.error_details = ''
            job.save()
            
            AuditLog.objects.create(
                event_type='JOB_RESUMED',
                organization_id=job.organization_id,
                job_id=str(job.job_id),
                outcome='SUCCESS',
                metadata={'from_stage': checkpoint.stage, 'position': checkpoint.page_position}
            )
            
            logger.info(f"Resumed job {job_id} from checkpoint stage {checkpoint.stage}")
            return job, checkpoint
        except (Job.DoesNotExist, JobCheckpoint.DoesNotExist) as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            raise
