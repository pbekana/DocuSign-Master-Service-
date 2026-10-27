"""
Normalization services for transforming raw DocuSign data.
"""
import json
import pandas as pd
from pathlib import Path
from apps.storage.models import OutputMetadata


class NormalizationService:
    """Normalizes raw DocuSign data into structured tables."""
    
    def __init__(self, job):
        """
        Initialize normalization service.
        
        Args:
            job: Job model instance
        """
        self.job = job
        self.raw_data_dir = Path(f'/tmp/docusign_jobs/{job.job_id}/raw')
        self.normalized_dir = Path(f'/tmp/docusign_jobs/{job.job_id}/normalized')
        self.normalized_dir.mkdir(parents=True, exist_ok=True)
    
    def normalize_all(self):
        """Normalize all data types and generate output files."""
        
        # Normalize envelopes
        envelopes_file = self.raw_data_dir / 'envelopes_complete.json'
        if envelopes_file.exists():
            self._normalize_envelopes(envelopes_file)
        
        # Normalize recipients
        recipients_file = self.raw_data_dir / 'recipients_complete.json'
        if recipients_file.exists():
            self._normalize_recipients(recipients_file)
        
        # Normalize documents
        documents_file = self.raw_data_dir / 'documents_complete.json'
        if documents_file.exists():
            self._normalize_documents(documents_file)
        
        # Normalize templates
        templates_file = self.raw_data_dir / 'templates_complete.json'
        if templates_file.exists():
            self._normalize_templates(templates_file)
    
    def _normalize_envelopes(self, raw_file):
        """Normalize envelopes data."""
        with open(raw_file, 'r') as f:
            raw_envelopes = json.load(f)
        
        if not raw_envelopes:
            return
        
        # Flatten envelope records
        records = []
        for envelope in raw_envelopes:
            record = {
                'envelope_id': envelope.get('envelopeId'),
                'status': envelope.get('status'),
                'email_subject': envelope.get('emailSubject'),
                'sender_name': envelope.get('sender', {}).get('userName'),
                'sender_email': envelope.get('sender', {}).get('email'),
                'created_datetime': envelope.get('createdDateTime'),
                'sent_datetime': envelope.get('sentDateTime'),
                'completed_datetime': envelope.get('completedDateTime'),
                'last_modified_datetime': envelope.get('lastModifiedDateTime'),
                'recipients_count': len(envelope.get('recipients', [])),
            }
            
            # Flatten custom fields if present
            custom_fields = envelope.get('customFields', {})
            if custom_fields:
                record['custom_fields'] = json.dumps(custom_fields)
            
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Save as JSON
        json_path = self.normalized_dir / 'envelopes.json'
        df.to_json(json_path, orient='records', lines=True)
        row_count = len(df)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='envelopes',
            format='JSON',
            row_count=row_count,
            local_path=str(json_path)
        )
        
        # Save as Parquet
        parquet_path = self.normalized_dir / 'envelopes.parquet'
        df.to_parquet(parquet_path, engine='pyarrow', index=False)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='envelopes',
            format='PARQUET',
            row_count=row_count,
            local_path=str(parquet_path)
        )
    
    def _normalize_recipients(self, raw_file):
        """Normalize recipients data."""
        with open(raw_file, 'r') as f:
            raw_recipients = json.load(f)
        
        if not raw_recipients:
            return
        
        # Flatten recipient records
        records = []
        for envelope_id, recipients_data in raw_recipients.items():
            if 'error' in recipients_data:
                continue
            
            # Handle different recipient types
            for recipient_type in ['signers', 'carbonCopies', 'certifiedDeliveries', 'agents']:
                for recipient in recipients_data.get(recipient_type, []):
                    record = {
                        'envelope_id': envelope_id,
                        'recipient_id': recipient.get('recipientId'),
                        'recipient_type': recipient_type,
                        'name': recipient.get('name'),
                        'email': recipient.get('email'),
                        'role_name': recipient.get('roleName'),
                        'status': recipient.get('status'),
                        'sent_datetime': recipient.get('sentDateTime'),
                        'delivered_datetime': recipient.get('deliveredDateTime'),
                        'signed_datetime': recipient.get('signedDateTime'),
                        'routing_order': recipient.get('routingOrder'),
                    }
                    records.append(record)
        
        if not records:
            return
        
        df = pd.DataFrame(records)
        
        # Save as JSON
        json_path = self.normalized_dir / 'recipients.json'
        df.to_json(json_path, orient='records', lines=True)
        row_count = len(df)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='recipients',
            format='JSON',
            row_count=row_count,
            local_path=str(json_path)
        )
        
        # Save as Parquet
        parquet_path = self.normalized_dir / 'recipients.parquet'
        df.to_parquet(parquet_path, engine='pyarrow', index=False)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='recipients',
            format='PARQUET',
            row_count=row_count,
            local_path=str(parquet_path)
        )
    
    def _normalize_documents(self, raw_file):
        """Normalize documents data."""
        with open(raw_file, 'r') as f:
            raw_documents = json.load(f)
        
        if not raw_documents:
            return
        
        # Flatten document records
        records = []
        for envelope_id, documents_data in raw_documents.items():
            if 'error' in documents_data:
                continue
            
            for document in documents_data.get('envelopeDocuments', []):
                record = {
                    'envelope_id': envelope_id,
                    'document_id': document.get('documentId'),
                    'document_name': document.get('name'),
                    'file_extension': document.get('fileExtension'),
                    'order': document.get('order'),
                    'pages': document.get('pages'),
                }
                records.append(record)
        
        if not records:
            return
        
        df = pd.DataFrame(records)
        
        # Save as JSON
        json_path = self.normalized_dir / 'documents.json'
        df.to_json(json_path, orient='records', lines=True)
        row_count = len(df)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='documents',
            format='JSON',
            row_count=row_count,
            local_path=str(json_path)
        )
        
        # Save as Parquet
        parquet_path = self.normalized_dir / 'documents.parquet'
        df.to_parquet(parquet_path, engine='pyarrow', index=False)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='documents',
            format='PARQUET',
            row_count=row_count,
            local_path=str(parquet_path)
        )
    
    def _normalize_templates(self, raw_file):
        """Normalize templates data."""
        with open(raw_file, 'r') as f:
            raw_templates = json.load(f)
        
        if not raw_templates:
            return
        
        # Flatten template records
        records = []
        for template in raw_templates:
            record = {
                'template_id': template.get('templateId'),
                'name': template.get('name'),
                'description': template.get('description'),
                'shared': template.get('shared'),
                'created_datetime': template.get('created'),
                'last_modified_datetime': template.get('lastModified'),
                'status': template.get('folderName'),
                'page_count': template.get('pageCount'),
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        # Save as JSON
        json_path = self.normalized_dir / 'templates.json'
        df.to_json(json_path, orient='records', lines=True)
        row_count = len(df)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='templates',
            format='JSON',
            row_count=row_count,
            local_path=str(json_path)
        )
        
        # Save as Parquet
        parquet_path = self.normalized_dir / 'templates.parquet'
        df.to_parquet(parquet_path, engine='pyarrow', index=False)
        
        OutputMetadata.objects.create(
            job=self.job,
            table_name='templates',
            format='PARQUET',
            row_count=row_count,
            local_path=str(parquet_path)
        )
