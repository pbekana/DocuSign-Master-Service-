"""Django management command to run the background job processing worker."""
import logging
import time
import signal
import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.jobs.models import Job
from apps.jobs.services import JobService, CheckpointService
from apps.authentication.services import DocuSignAuthService
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the DocuSign extraction worker process'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle graceful shutdown."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--poll-interval',
            type=int,
            default=5,
            help='Poll interval in seconds (default: 5)'
        )
        parser.add_argument(
            '--heartbeat-interval',
            type=int,
            default=30,
            help='Heartbeat update interval in seconds (default: 30)'
        )
    
    def handle(self, *args, **options):
        """Main worker loop."""
        poll_interval = options['poll_interval']
        heartbeat_interval = options['heartbeat_interval']
        
        self.stdout.write(self.style.SUCCESS('Starting DocuSign extraction worker...'))
        logger.info("Worker started")
        
        last_heartbeat_update = {}
        
        while self.running:
            try:
                # Claim a pending job using SELECT FOR UPDATE to prevent concurrent processing
                with transaction.atomic():
                    job = Job.objects.select_for_update(skip_locked=True).filter(
                        status='PENDING'
                    ).first()
                    
                    if job:
                        # Found a job to process
                        logger.info(f"Claimed job {job.job_id}")
                        self._process_job(job, last_heartbeat_update, heartbeat_interval)
                
                # Wait before checking for next job
                time.sleep(poll_interval)
            
            except KeyboardInterrupt:
                logger.info("Worker interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                time.sleep(poll_interval)
        
        self.stdout.write(self.style.SUCCESS('Worker stopped'))
        logger.info("Worker stopped")
    
    def _process_job(self, job, last_heartbeat_update, heartbeat_interval):
        """Process a single job through its extraction stages."""
        job_id = str(job.job_id)
        last_heartbeat_update[job_id] = time.time()
        
        try:
            # Update status to FETCHING_ENVELOPES
            JobService.update_status(job_id, 'FETCHING_ENVELOPES', stage='FETCHING_ENVELOPES')
            
            # Check for cancellation
            if self._check_cancellation(job_id):
                logger.info(f"Job {job_id} was cancelled, stopping")
                return
            
            # Update heartbeat
            JobService.update_heartbeat(job_id)
            
            # Simulate extraction stages
            stages = [
                ('FETCHING_ENVELOPES', 'Fetching envelopes...'),
                ('FETCHING_DETAILS', 'Fetching recipient and document details...'),
                ('NORMALIZING', 'Normalizing extracted data...'),
                ('UPLOADING_TO_MINIO', 'Uploading to MinIO...'),
            ]
            
            for stage_name, description in stages:
                logger.info(f"Job {job_id} stage: {description}")
                
                # Check for cancellation between stages
                if self._check_cancellation(job_id):
                    logger.info(f"Job {job_id} was cancelled during {stage_name}")
                    return
                
                # Update heartbeat periodically
                current_time = time.time()
                if current_time - last_heartbeat_update.get(job_id, 0) >= heartbeat_interval:
                    JobService.update_heartbeat(job_id)
                    last_heartbeat_update[job_id] = current_time
                
                # Update job progress
                JobService.update_progress(
                    job_id,
                    {'current_stage': stage_name, 'items_processed': 0},
                    {'envelopes': 0, 'recipients': 0, 'documents': 0, 'templates': 0}
                )
                
                # Simulate work
                time.sleep(1)
                
                # Update status to next stage
                next_stage_index = [s[0] for s in stages].index(stage_name) + 1
                if next_stage_index < len(stages):
                    JobService.update_status(job_id, stages[next_stage_index][0], stage=stages[next_stage_index][0])
            
            # Mark job as completed
            JobService.update_status(job_id, 'COMPLETED', stage='COMPLETED')
            
            AuditLog.objects.create(
                event_type='EXTRACTION_COMPLETED',
                organization_id=job.organization_id,
                job_id=job_id,
                outcome='SUCCESS',
                metadata={'record_counts': job.record_counts}
            )
            
            logger.info(f"Job {job_id} completed successfully")
            self.stdout.write(self.style.SUCCESS(f"✓ Job {job_id} completed"))
        
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            
            try:
                JobService.update_status(
                    job_id,
                    'FAILED',
                    stage='ERROR',
                    error_details=str(e)
                )
                
                AuditLog.objects.create(
                    event_type='EXTRACTION_FAILED',
                    organization_id=job.organization_id,
                    job_id=job_id,
                    outcome='FAILURE',
                    metadata={'error': str(e)}
                )
            except Exception as update_error:
                logger.error(f"Failed to update job status for {job_id}: {update_error}")
            
            self.stdout.write(self.style.ERROR(f"✗ Job {job_id} failed: {e}"))
    
    def _check_cancellation(self, job_id):
        """Check if job has been cancelled."""
        try:
            job = Job.objects.get(job_id=job_id)
            return job.status == 'CANCELLED'
        except Job.DoesNotExist:
            return False
