"""
Extraction services for DocuSign data.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from apps.extraction.client import DocuSignClient


class ExtractionService:
    """Orchestrates DocuSign data extraction."""
    
    def __init__(self, client: DocuSignClient, job):
        """
        Initialize extraction service.
        
        Args:
            client: DocuSignClient instance
            job: Job model instance
        """
        self.client = client
        self.job = job
        self.raw_data_dir = Path(f'/tmp/docusign_jobs/{job.job_id}/raw')
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_envelopes(self, checkpoint=None):
        """
        Extract envelopes with pagination.
        
        Args:
            checkpoint: JobCheckpoint instance or None
        
        Returns:
            list: All extracted envelope records
        """
        start_position = 0
        if checkpoint and checkpoint.page_position:
            start_position = checkpoint.page_position.get('start_position', 0)
        
        all_envelopes = []
        date_from = self.job.date_from.strftime('%Y-%m-%d')
        date_to = self.job.date_to.strftime('%Y-%m-%d')
        
        while True:
            # Fetch page
            response = self.client.get_envelopes(
                start_date=date_from,
                end_date=date_to,
                start_position=start_position,
                count=100
            )
            
            envelopes = response.get('envelopes', [])
            if not envelopes:
                break
            
            all_envelopes.extend(envelopes)
            
            # Save page to file
            page_file = self.raw_data_dir / f'envelopes_page_{start_position}.json'
            with open(page_file, 'w') as f:
                json.dump(envelopes, f, indent=2)
            
            # Check if more pages exist
            result_set_size = response.get('resultSetSize', len(envelopes))
            total_set_size = response.get('totalSetSize', len(envelopes))
            
            start_position += result_set_size
            
            if start_position >= total_set_size:
                break
        
        # Save complete envelopes file
        envelopes_file = self.raw_data_dir / 'envelopes_complete.json'
        with open(envelopes_file, 'w') as f:
            json.dump(all_envelopes, f, indent=2)
        
        return all_envelopes
    
    def extract_recipients(self, envelope_ids, checkpoint=None):
        """
        Extract recipients for given envelope IDs.
        
        Args:
            envelope_ids: List of envelope IDs
            checkpoint: JobCheckpoint instance or None
        
        Returns:
            dict: Mapping of envelope_id to recipients
        """
        start_index = 0
        if checkpoint and checkpoint.checkpoint_data:
            start_index = checkpoint.checkpoint_data.get('recipient_index', 0)
        
        recipients_map = {}
        
        for idx, envelope_id in enumerate(envelope_ids[start_index:], start=start_index):
            try:
                recipients_data = self.client.get_envelope_recipients(envelope_id)
                recipients_map[envelope_id] = recipients_data
            except Exception as e:
                # Log error but continue
                recipients_map[envelope_id] = {'error': str(e)}
        
        # Save recipients data
        recipients_file = self.raw_data_dir / 'recipients_complete.json'
        with open(recipients_file, 'w') as f:
            json.dump(recipients_map, f, indent=2)
        
        return recipients_map
    
    def extract_documents(self, envelope_ids, checkpoint=None):
        """
        Extract document metadata for given envelope IDs.
        
        Args:
            envelope_ids: List of envelope IDs
            checkpoint: JobCheckpoint instance or None
        
        Returns:
            dict: Mapping of envelope_id to documents
        """
        start_index = 0
        if checkpoint and checkpoint.checkpoint_data:
            start_index = checkpoint.checkpoint_data.get('document_index', 0)
        
        documents_map = {}
        
        for idx, envelope_id in enumerate(envelope_ids[start_index:], start=start_index):
            try:
                documents_data = self.client.get_envelope_documents(envelope_id)
                documents_map[envelope_id] = documents_data
            except Exception as e:
                # Log error but continue
                documents_map[envelope_id] = {'error': str(e)}
        
        # Save documents data
        documents_file = self.raw_data_dir / 'documents_complete.json'
        with open(documents_file, 'w') as f:
            json.dump(documents_map, f, indent=2)
        
        return documents_map
    
    def extract_templates(self, checkpoint=None):
        """
        Extract templates with pagination.
        
        Args:
            checkpoint: JobCheckpoint instance or None
        
        Returns:
            list: All extracted template records
        """
        start_position = 0
        if checkpoint and checkpoint.page_position:
            start_position = checkpoint.page_position.get('start_position', 0)
        
        all_templates = []
        
        while True:
            # Fetch page
            response = self.client.get_templates(
                start_position=start_position,
                count=100
            )
            
            templates = response.get('envelopeTemplates', [])
            if not templates:
                break
            
            all_templates.extend(templates)
            
            # Save page to file
            page_file = self.raw_data_dir / f'templates_page_{start_position}.json'
            with open(page_file, 'w') as f:
                json.dump(templates, f, indent=2)
            
            # Check if more pages exist
            result_set_size = response.get('resultSetSize', len(templates))
            total_set_size = response.get('totalSetSize', len(templates))
            
            start_position += result_set_size
            
            if start_position >= total_set_size:
                break
        
        # Save complete templates file
        templates_file = self.raw_data_dir / 'templates_complete.json'
        with open(templates_file, 'w') as f:
            json.dump(all_templates, f, indent=2)
        
        return all_templates
