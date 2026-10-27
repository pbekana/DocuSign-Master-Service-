"""
Tests for job management functionality.
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone
from apps.jobs.models import Job
from apps.jobs.services import JobService, CheckpointService


@pytest.mark.django_db
class TestJobService:
    """Test job service operations."""
    
    def test_create_job(self):
        """Test creating a new job."""
        job = JobService.create_job(
            organization_id='org-123',
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            extraction_config={'test': 'config'}
        )
        
        assert job.job_id is not None
        assert job.organization_id == 'org-123'
        assert job.status == 'PENDING'
        assert job.date_from == date(2024, 1, 1)
        assert job.date_to == date(2024, 1, 31)
    
    def test_update_status(self):
        """Test updating job status."""
        job = JobService.create_job(
            organization_id='org-123',
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31)
        )
        
        JobService.update_status(job.job_id, 'FETCHING_ENVELOPES', 'Starting extraction')
        
        job.refresh_from_db()
        assert job.status == 'FETCHING_ENVELOPES'
        assert job.current_stage == 'Starting extraction'
        assert job.started_at is not None
    
    def test_cancel_job(self):
        """Test cancelling a job."""
        job = JobService.create_job(
            organization_id='org-123',
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31)
        )
        
        result = JobService.cancel_job(job.job_id)
        
        assert result is True
        job.refresh_from_db()
        assert job.status == 'CANCELLED'
    
    def test_list_jobs(self):
        """Test listing jobs with filters."""
        JobService.create_job('org-1', date(2024, 1, 1), date(2024, 1, 31))
        JobService.create_job('org-2', date(2024, 2, 1), date(2024, 2, 28))
        JobService.create_job('org-1', date(2024, 3, 1), date(2024, 3, 31))
        
        all_jobs = JobService.list_jobs()
        assert len(all_jobs) == 3
        
        org1_jobs = JobService.list_jobs(organization_id='org-1')
        assert len(org1_jobs) == 2


@pytest.mark.django_db
class TestCheckpointService:
    """Test checkpoint service operations."""
    
    def test_save_checkpoint(self):
        """Test saving a checkpoint."""
        job = JobService.create_job(
            organization_id='org-123',
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31)
        )
        
        checkpoint = CheckpointService.save_checkpoint(
            job.job_id,
            'envelopes',
            page_position={'start_position': 100},
            records_processed=100
        )
        
        assert checkpoint.job_id == job.job_id
        assert checkpoint.stage == 'envelopes'
        assert checkpoint.page_position['start_position'] == 100
    
    def test_get_latest_checkpoint(self):
        """Test retrieving latest checkpoint."""
        job = JobService.create_job(
            organization_id='org-123',
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31)
        )
        
        CheckpointService.save_checkpoint(job.job_id, 'envelopes', page_position={'start_position': 0})
        CheckpointService.save_checkpoint(job.job_id, 'envelopes', page_position={'start_position': 100})
        
        latest = CheckpointService.get_latest_checkpoint(job.job_id, 'envelopes')
        assert latest.page_position['start_position'] == 100
    
    def test_resume_job(self):
        """Test resuming a failed job."""
        job = JobService.create_job(
            organization_id='org-123',
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31)
        )
        
        # Simulate a failed job with checkpoint
        JobService.update_status(job.job_id, 'FAILED')
        CheckpointService.save_checkpoint(job.job_id, 'envelopes', page_position={'start_position': 50})
        
        success, checkpoint, message = CheckpointService.resume_job(job.job_id)
        
        assert success is True
        assert checkpoint is not None
        job.refresh_from_db()
        assert job.status == 'FETCHING_ENVELOPES'
