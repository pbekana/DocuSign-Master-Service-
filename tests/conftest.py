"""
Pytest configuration and fixtures for testing.
"""
import pytest
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_setup():
    """Configure test database settings."""
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }


@pytest.fixture
def sample_envelope():
    """Sample envelope data from DocuSign API."""
    return {
        'envelopeId': 'env-123',
        'status': 'completed',
        'emailSubject': 'Test Document',
        'sender': {
            'userName': 'John Doe',
            'email': 'john@example.com'
        },
        'createdDateTime': '2024-01-01T10:00:00Z',
        'sentDateTime': '2024-01-01T10:05:00Z',
        'completedDateTime': '2024-01-01T11:00:00Z',
        'lastModifiedDateTime': '2024-01-01T11:00:00Z'
    }


@pytest.fixture
def sample_recipient():
    """Sample recipient data from DocuSign API."""
    return {
        'signers': [{
            'recipientId': 'rec-123',
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'roleName': 'Signer',
            'status': 'completed',
            'sentDateTime': '2024-01-01T10:05:00Z',
            'deliveredDateTime': '2024-01-01T10:10:00Z',
            'signedDateTime': '2024-01-01T11:00:00Z',
            'routingOrder': '1'
        }]
    }


@pytest.fixture
def sample_document():
    """Sample document data from DocuSign API."""
    return {
        'envelopeDocuments': [{
            'documentId': 'doc-123',
            'name': 'Contract.pdf',
            'fileExtension': 'pdf',
            'order': '1',
            'pages': '5'
        }]
    }


@pytest.fixture
def sample_template():
    """Sample template data from DocuSign API."""
    return {
        'templateId': 'tmp-123',
        'name': 'Standard Contract',
        'description': 'A standard contract template',
        'shared': 'false',
        'created': '2024-01-01T00:00:00Z',
        'lastModified': '2024-01-01T00:00:00Z',
        'folderName': 'Active',
        'pageCount': '3'
    }
