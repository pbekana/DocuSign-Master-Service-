# DocuSign Master Service

A complete Django-based backend data extraction service that extracts data from DocuSign accounts, normalizes it into clean tables (JSON and Parquet), and uploads outputs to MinIO object storage.

## Project Purpose

The DocuSign Master Service:
- **Extracts** envelope, recipient, document, and template data from DocuSign accounts
- **Handles** pagination, rate limiting, API failures, and interrupted jobs
- **Normalizes** raw API responses into clean, consistent data tables
- **Generates** both JSON and Parquet output files
- **Uploads** normalized outputs to MinIO object storage
- **Provides** a REST API for an external Coordinator system to manage extraction jobs
- **Recovers** from crashes using checkpoint-based resumption
- **Audits** all operational and security events

## Technology Stack

- **Backend**: Python 3.11, Django 4.2, Django REST Framework
- **Database**: PostgreSQL 15
- **Object Storage**: MinIO
- **Data Processing**: Pandas, PyArrow (for Parquet)
- **External APIs**: DocuSign eSignature REST API v2.1
- **Containerization**: Docker, Docker Compose
- **Testing**: pytest, pytest-django
- **HTTP Client**: requests

## Directory Structure

```
docusign-master-service/
├── manage.py                      # Django management script
├── config/                        # Django project configuration
│   ├── settings.py                # Django settings
│   ├── urls.py                    # URL routing
│   ├── wsgi.py                    # WSGI application
│   └── asgi.py                    # ASGI application
├── apps/                          # Django applications
│   ├── jobs/                      # Job management and background worker
│   ├── authentication/            # DocuSign auth + HMAC security
│   ├── extraction/                # DocuSign API extraction
│   ├── normalization/             # Data normalization and Parquet generation
│   ├── storage/                   # MinIO storage integration
│   ├── audit/                     # Audit logging and monitoring
│   └── resilience/                # Rate limiting, retries, recovery
├── common/                        # Shared utilities and views
├── tests/                         # Automated tests
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variable template
├── .gitignore                     # Git ignore rules
├── Dockerfile                     # Container image definition
├── docker-compose.yml             # Docker Compose configuration
├── README.md                      # This file
└── DESIGN.md                      # Architecture and design documentation
```

## Installation

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 12 or higher
- MinIO (for local development, can use Docker)
- DocuSign developer account with integration credentials
- Docker and Docker Compose (for containerized deployment)

### Local Development Setup

#### 1. Clone and Navigate to Project

```bash
cd "/home/simon/Downloads/DocuSign Master Service"
```

#### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

Copy the environment template and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key-for-development
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DATABASE_URL=postgresql://docusign_user:docusign_password@localhost:5432/docusign_db

# DocuSign Configuration
DOCUSIGN_INTEGRATION_KEY=your_integration_key_from_docusign
DOCUSIGN_USER_ID=your_docusign_user_id
DOCUSIGN_PRIVATE_KEY_PATH=/path/to/your/private/key.pem
DOCUSIGN_AUTH_SERVER=https://account-d.docusign.com

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=docusign

# HMAC Authentication
HMAC_ENABLED=True
HMAC_SECRET_KEY_CORE=your_coordinator_secret_key
HMAC_SECRET_KEY_ENGINEER=your_engineer_read_only_key
```

#### 5. Set Up PostgreSQL Database

```bash
# Create database and user (if not using Docker)
createuser -P docusign_user
createdb -O docusign_user docusign_db
```

#### 6. Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 7. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

#### 8. Verify Installation

```bash
python manage.py check
```

## Running the Application

### Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Server will be available at `http://localhost:8000/api/health`

### Background Worker

In a separate terminal:

```bash
python manage.py run_scan_worker --poll-interval 5 --heartbeat-interval 30
```

The worker processes pending extraction jobs in the background.

### Using Docker Compose

#### Build Images

```bash
docker-compose build
```

#### Start Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL database
- MinIO object storage (accessible at `http://localhost:9001`)
- Django API (port 8000)
- Background worker

#### View Logs

```bash
docker-compose logs -f django-app
docker-compose logs -f worker
```

#### Stop Services

```bash
docker-compose down
```

#### Database Migrations with Docker

```bash
docker-compose run django-app python manage.py migrate
```

## API Endpoints

All endpoints require HMAC authentication (except `/api/health` and `/api/stats`).

### Scan Management

**Start a new extraction job:**
```http
POST /api/scan/start
Content-Type: application/json
X-DS-Signature: <hmac-signature>
X-DS-Timestamp: <unix-timestamp>
X-DS-Client-ID: coordinator
X-DS-Nonce: <unique-nonce>

{
  "organization_id": "org-123",
  "date_from": "2024-01-01T00:00:00Z",
  "date_to": "2024-01-31T23:59:59Z",
  "extraction_config": {}
}
```

**Response (202 Accepted):**
```json
{
  "scan_id": "uuid-of-job",
  "status": "PENDING",
  "message": "Job queued for processing"
}
```

**Get job status:**
```http
GET /api/scan/{scan_id}/status
```

**Cancel a job:**
```http
POST /api/scan/{scan_id}/cancel
```

**Resume a failed job:**
```http
POST /api/scan/{scan_id}/resume
```

**List all jobs:**
```http
GET /api/scan/list?organization_id=org-123&status=COMPLETED&limit=100&offset=0
```

**Get job statistics:**
```http
GET /api/scan/statistics?organization_id=org-123
```

**Delete a job:**
```http
DELETE /api/scan/{scan_id}/remove
```

### Normalization

**Trigger normalization:**
```http
POST /api/normalization/{scan_id}/normalize
```

**List tables for a job:**
```http
GET /api/normalization/{scan_id}/tables
```

**Get supported object types:**
```http
GET /api/normalization/supported-objects
```

### Credentials

**Validate DocuSign credentials:**
```http
POST /api/validate-credentials
```

### Maintenance

**Cleanup old jobs and nonces:**
```http
POST /api/maintenance/cleanup
```

**Detect crashed jobs:**
```http
POST /api/maintenance/detect-crashed
```

### Audit

**Get audit logs:**
```http
GET /api/audit/logs?organization_id=org-123&event_type=JOB_CREATED&limit=100&offset=0
```

**Get audit statistics:**
```http
GET /api/audit/stats?organization_id=org-123
```

### Health & Statistics

**Health check (public):**
```http
GET /api/health
```

**Service statistics (public):**
```http
GET /api/stats
```

## HMAC Authentication

The Coordinator must authenticate requests using HMAC-SHA256 signatures.

### Canonical Request Format

```
METHOD
PATH
TIMESTAMP
NONCE
SHA256(BODY)
```

### Signature Generation Example (Python)

```python
import hashlib
import hmac
import time
from datetime import datetime

def generate_signature(method, path, body, secret_key):
    timestamp = str(int(time.time()))
    nonce = f"nonce-{datetime.utcnow().isoformat()}"
    
    body_hash = hashlib.sha256(body.encode() if isinstance(body, str) else body).hexdigest()
    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    
    signature = hmac.new(
        secret_key.encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature, timestamp, nonce

method = "POST"
path = "/api/scan/start"
body = '{"organization_id": "org-123", "date_from": "2024-01-01T00:00:00Z", "date_to": "2024-01-31T23:59:59Z"}'
secret_key = "your_coordinator_secret_key"

signature, timestamp, nonce = generate_signature(method, path, body, secret_key)

headers = {
    "X-DS-Signature": signature,
    "X-DS-Timestamp": timestamp,
    "X-DS-Client-ID": "coordinator",
    "X-DS-Nonce": nonce,
    "Content-Type": "application/json"
}

# Send POST request with headers
```

### Permission Levels

- **Coordinator key** (`X-DS-Client-ID: coordinator`): Can perform all operations (create, cancel, resume, delete jobs)
- **Engineer key** (`X-DS-Client-ID: engineer`): Read-only access to inspect jobs and logs

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `APP_ENV` | Environment (development, staging, production) | development | No |
| `DEBUG` | Django debug mode | False | No |
| `SECRET_KEY` | Django secret key | generated | Yes (production) |
| `DATABASE_URL` | PostgreSQL connection string | sqlite3 | No |
| `DOCUSIGN_INTEGRATION_KEY` | DocuSign integration key | | Yes |
| `DOCUSIGN_USER_ID` | DocuSign user ID | | Yes |
| `DOCUSIGN_PRIVATE_KEY_PATH` | Path to RSA private key | | Yes |
| `DOCUSIGN_AUTH_SERVER` | DocuSign OAuth server | https://account-d.docusign.com | No |
| `MINIO_ENDPOINT` | MinIO endpoint | localhost:9000 | No |
| `MINIO_ACCESS_KEY` | MinIO access key | minioadmin | No |
| `MINIO_SECRET_KEY` | MinIO secret key | minioadmin | No |
| `MINIO_BUCKET_NAME` | MinIO bucket name | docusign | No |
| `HMAC_ENABLED` | Enable HMAC authentication | True | No |
| `HMAC_SECRET_KEY_CORE` | Coordinator HMAC secret | | Yes |
| `HMAC_SECRET_KEY_ENGINEER` | Engineer HMAC secret | | Yes |
| `RETENTION_DAYS` | Cleanup retention days | 90 | No |
| `HEARTBEAT_TIMEOUT_MINUTES` | Crash detection timeout | 10 | No |

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_hmac_auth.py -v
```

### Run with Coverage

```bash
pytest tests/ --cov=apps --cov-report=html
```

### Test Database

Tests use a temporary SQLite database. Configure in `tests/conftest.py` if needed.

## DocuSign Configuration

### Prerequisites

1. **Create DocuSign Developer Account**: Visit [DocuSign Developer](https://developer.docusign.com/)

2. **Create Integration Key**: In the DocuSign Admin console:
   - Settings → Apps and Keys
   - Create Integrations Key
   - Generate RSA keypair
   - Save private key to secure location

3. **Add Scopes**: Add `signature` and `impersonation` scopes to the key

4. **Configure Redirect URI**: For Authorization Code flow (if used)

### JWT Grant (Server-to-Server)

For service-to-service authentication:

1. Get Integration Key and User ID
2. Generate RSA private key
3. Set environment variables in `.env`
4. Service will authenticate automatically using JWT

## Database Schema

### Models

**Job**: Tracks extraction jobs
- `job_id`: UUID primary key
- `organization_id`: Organization identifier
- `status`: Current state (PENDING, FETCHING_ENVELOPES, COMPLETED, FAILED, CRASHED, CANCELLED)
- `date_from`, `date_to`: Date range for extraction
- `progress`: JSON field tracking current stage and progress
- `record_counts`: JSON field with counts by record type
- `created_at`, `started_at`, `completed_at`: Timestamps

**JobCheckpoint**: Persists extraction progress for recovery
- `job`: Foreign key to Job
- `stage`: Current extraction stage
- `page_position`: Pagination position for resumption
- `records_processed`: Number of records processed
- `last_envelope_id`: Last processed envelope ID

**AuditLog**: Records operational and security events
- `event_type`: Type of event
- `organization_id`, `client_id`: Context information
- `outcome`: SUCCESS, FAILURE, etc.
- `metadata`: JSON additional information

**FailedExternalCall**: Tracks external operations that failed after retries
- `service`, `operation`: What failed
- `attempts`, `last_error`: Retry information
- `status`: Current retry status

**NonceStore**: Prevents HMAC replay attacks
- `nonce`: Unique request nonce
- `client_id`: Client identifier
- `created_at`: Creation timestamp

**OutputMetadata**: Tracks generated output files
- `job_id`: Associated job
- `table_name`: Data table name
- `format`: JSON or Parquet
- `row_count`: Number of rows
- `minio_key`: MinIO object path
- `uploaded_at`: Upload timestamp

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
psql -U docusign_user -d docusign_db -c "SELECT 1"

# Check Django database configuration
python manage.py dbshell
```

### Migration Errors

```bash
# Show current migrations
python manage.py showmigrations

# Reset migrations (development only)
python manage.py migrate apps.jobs zero
python manage.py makemigrations
python manage.py migrate
```

### DocuSign Authentication Failures

1. Verify integration key and user ID
2. Check private key file path and permissions
3. Ensure private key format is PEM
4. Test with validation endpoint: `POST /api/validate-credentials`

### MinIO Connection Issues

```bash
# Check MinIO is running and accessible
curl -X GET http://localhost:9000/minio/health/live

# Verify credentials and bucket exist
```

### Worker Not Processing Jobs

1. Check worker is running: `python manage.py run_scan_worker`
2. Verify database connection
3. Check for error logs
4. Ensure job status is `PENDING`

## Known Limitations

- Extraction is simulated in the current worker implementation (no actual DocuSign API calls)
- Normalization to Parquet requires pandas and pyarrow installation
- MinIO storage is simulated (requires configuration for real uploads)
- Rate limiting and retry logic is implemented but not fully tested with real DocuSign API

## Performance Considerations

- **Worker Scaling**: Multiple worker instances can process jobs concurrently using PostgreSQL locks
- **Database Indexes**: Key indexes on `job_id`, `organization_id`, `status`, and timestamps
- **Checkpoint Frequency**: Balance between recovery granularity and database load
- **Batch Processing**: Extract and checkpoint in configurable page sizes

## Security Notes

- Never commit `.env` or `.env.local` files
- Rotate HMAC secrets regularly in production
- Use environment variables for all secrets
- Enable HTTPS in production
- Implement rate limiting at infrastructure level
- Audit logs don't contain sensitive data (tokens, passwords, PII)

## Support and Contribution

For issues or questions:
1. Check the DESIGN.md for architecture details
2. Review audit logs for event details
3. Enable DEBUG mode for detailed error information
4. Check PostgreSQL and MinIO connectivity

## License

© 2024 DocuSign Master Service. All rights reserved.
