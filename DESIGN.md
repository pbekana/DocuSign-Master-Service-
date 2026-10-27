# DocuSign Master Service - Architecture & Design

## System Architecture

### Overview

The DocuSign Master Service is a modular Django-based backend that orchestrates data extraction from DocuSign accounts, normalizes the data, and publishes it to MinIO. The system is designed for reliability, scalability, and observability.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Coordinator (External)                   │
│                    REST API + HMAC Authentication                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Django REST API Application                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Authentication Middleware                                │  │
│  │  • HMAC-SHA256 signature validation                      │  │
│  │  • Nonce replay protection (PostgreSQL-backed)           │  │
│  │  • Permission enforcement (read-only vs write)           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌──────────┬─────────────┼────────────┬─────────────────────┐  │
│  ▼          ▼             ▼            ▼                     ▼  │
│ Jobs    Extraction   Normalization  Storage               Audit  │
│ Views    Services     Services      Services              Logs   │
└─────────────────────────────────────────────────────────────────┘
         │                                         │
         ▼                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Job Management:  Job, JobCheckpoint                    │   │
│  │ Authentication:  NonceStore (replay protection)         │   │
│  │ Audit:          AuditLog, FailedExternalCall           │   │
│  │ Storage:        OutputMetadata                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Background Worker (Django Management Command)      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Poll database for PENDING jobs (with locking)        │  │
│  │ 2. Process extraction stages with heartbeat updates     │  │
│  │ 3. Save checkpoints after each stage                    │  │
│  │ 4. Check for cancellation between work units            │  │
│  │ 5. Update job status and record counts                  │  │
│  │ 6. Handle failures and mark as CRASHED or FAILED        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  External Services                              │
│  ┌──────────────────────────┬───────────────────────────────┐  │
│  ▼                          ▼                               ▼  │
│ DocuSign API            MinIO Object Storage          PostgreSQL│
│ (Envelopes,            (Parquet + JSON files)         (Primary  │
│  Recipients,                                           Database)│
│  Documents,                                                    │
│  Templates)                                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Django Application Modules

### 1. **apps/jobs** - Job Management & Worker

**Responsibility**: Create, track, and manage extraction jobs throughout their lifecycle.

**Models**:
- `Job`: Main extraction job record with status, progress, and timestamps
- `JobCheckpoint`: Persists extraction state for recovery

**Services**:
- `JobService`: Job CRUD, status transitions, progress updates
- `CheckpointService`: Checkpoint save/load, recovery logic

**Views**:
- `StartScanView` (POST /api/scan/start): Create job, return 202
- `ScanStatusView` (GET /api/scan/{id}/status): Job details
- `CancelScanView` (POST /api/scan/{id}/cancel): Set status to CANCELLED
- `ResumeScanView` (POST /api/scan/{id}/resume): Resume from checkpoint
- `ListScansView` (GET /api/scan/list): List with pagination and filters
- `ScanStatisticsView` (GET /api/scan/statistics): Job stats by status

**Management Command**:
- `run_scan_worker`: Background worker that processes PENDING jobs

### 2. **apps/authentication** - Authentication & Security

**Responsibility**: Handle DocuSign API authentication and Coordinator HMAC security.

**Middleware**:
- `HMACAuthenticationMiddleware`: Validates request signatures, timestamps, nonces
  - Constant-time signature comparison to prevent timing attacks
  - Timestamp freshness validation (max 5 minutes old)
  - Nonce replay protection using PostgreSQL NonceStore
  - Permission enforcement (coordinator write, engineer read-only)

**Services**:
- `DocuSignAuthService`:
  - JWT Grant flow for server-to-server auth
  - Token caching with expiry awareness
  - Account base URL resolution
  - Credential validation without job creation

**Models**:
- `NonceStore`: Tracks used nonces for replay protection

### 3. **apps/extraction** - DocuSign Data Extraction

**Responsibility**: Call DocuSign APIs and extract envelope, recipient, document, and template data.

**Services** (to implement):
- `EnvelopeExtractionService`: Paginated envelope fetching with date filters
- `RecipientExtractionService`: Fetch recipients per envelope
- `DocumentExtractionService`: Fetch document metadata per envelope
- `TemplateExtractionService`: Paginated template extraction

**Rate Limiting & Retry**:
- Detect HTTP 429 (rate limit) responses
- Parse and honor `Retry-After` header
- Implement exponential backoff with jitter for transient failures
- After retry exhaustion, record to `FailedExternalCall` model

### 4. **apps/normalization** - Data Normalization

**Responsibility**: Transform raw DocuSign responses into clean, consistent schemas.

**Normalizers** (to implement):
- `EnvelopeNormalizer`: Flatten envelope objects, normalize timestamps
- `RecipientNormalizer`: Flatten recipient arrays, extract key fields
- `DocumentNormalizer`: Transform document metadata
- `TemplateNormalizer`: Normalize template data

**Output Formats**:
- **JSON**: Newline-delimited JSON for streaming and readability
- **Parquet**: Apache Parquet using PyArrow for efficient columnar storage

**Schema Stability**:
- Consistent column names across runs
- Handle missing/null values gracefully
- Support empty result sets

### 5. **apps/storage** - MinIO Integration

**Responsibility**: Upload normalized outputs to MinIO object storage.

**Services** (to implement):
- `MinIOStorageService`:
  - Bucket creation/verification
  - Object upload with retry logic
  - Key pattern: `docusign/{table_name}/glynac_organization_id={org_id}/processing_date={date}/{table}.parquet`
  - Upload verification and metadata recording

### 6. **apps/audit** - Audit Logging

**Responsibility**: Record operational and security events for compliance and debugging.

**Models**:
- `AuditLog`: Event type, organization, client, outcome, metadata
- `FailedExternalCall`: Track external operations that failed after retries
- `OutputMetadata`: Track generated files and their locations

**Events Logged**:
- Authentication success/failure, HMAC validation
- Job creation, status changes, cancellation, resumption
- Extraction start/completion/failure
- Rate limiting, retry exhaustion
- Normalization results
- MinIO uploads
- Maintenance operations
- Crash detection

### 7. **apps/resilience** - Reliability & Recovery

**Responsibility**: Handle failures, retries, and job recovery.

**Features**:
- **Rate Limiting**: HTTP 429 detection and backoff
- **Retry Logic**: Exponential backoff for transient errors
- **Checkpoint Recovery**: Load last checkpoint and resume work
- **Heartbeat Monitoring**: Detect crashed workers
- **Dead-Letter Queue**: Track operations that exhausted retries

## Job Lifecycle State Machine

```
┌─────────────┐
│   PENDING   │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│ FETCHING_ENVELOPES   │ ─────────────┐
└──────┬───────────────┘              │
       │                              ▼
       │                        ┌──────────┐
       ▼                        │  FAILED  │
┌──────────────────────┐        └──────────┘
│  FETCHING_DETAILS    │             ▲
└──────┬───────────────┘              │
       │                              │
       ▼                              │
┌──────────────────────┐              │
│   NORMALIZING        │ ────────────┤
└──────┬───────────────┘              │
       │                              │
       ▼                              │
┌──────────────────────┐              │
│ UPLOADING_TO_MINIO   │ ────────────┤
└──────┬───────────────┘              │
       │                              │
       ▼                              │
┌──────────────────────┐              │
│    COMPLETED         │         Any stage can
└──────────────────────┘         also transition to:
                                 - CANCELLED
                                 - CRASHED
                                 - FAILED
```

**Valid Transitions**:
- `PENDING` → `FETCHING_ENVELOPES` or `CANCELLED`
- `FETCHING_ENVELOPES` → `FETCHING_DETAILS`, `FAILED`, `CRASHED`, `CANCELLED`
- `FETCHING_DETAILS` → `NORMALIZING`, `FAILED`, `CRASHED`, `CANCELLED`
- `NORMALIZING` → `UPLOADING_TO_MINIO`, `FAILED`, `CRASHED`, `CANCELLED`
- `UPLOADING_TO_MINIO` → `COMPLETED`, `FAILED`, `CRASHED`, `CANCELLED`
- `FAILED` or `CRASHED` → `FETCHING_ENVELOPES` (resume from checkpoint)

## Checkpoint and Recovery Mechanism

### Checkpoint Data Structure

```python
{
    'job_id': 'uuid',
    'stage': 'FETCHING_ENVELOPES',  # Current stage
    'page_position': 100,            # Pagination position
    'records_processed': 1000,       # Total records so far
    'last_envelope_id': 'xyz',      # Last processed envelope
    'last_document_id': 'abc',      # Last processed document
    'timestamp': '2024-01-15T10:30:00Z'
}
```

### Recovery Process

1. **Detect Crash**: Job in active state with `last_heartbeat` older than timeout
2. **Mark as CRASHED**: Set job status to `CRASHED`
3. **Load Checkpoint**: Retrieve most recent `JobCheckpoint`
4. **Resume**: Reset job status to appropriate extraction stage with loaded position
5. **Continue**: Worker fetches next page/envelope from saved position
6. **Avoid Duplication**: Skip records before checkpoint position

### Heartbeat Mechanism

- Worker updates `job.last_heartbeat` every 30 seconds during processing
- Maintenance command checks for jobs with stale heartbeats (>10 min)
- Marks such jobs as `CRASHED` for eventual resumption

## HMAC Authentication Flow

### Request Signing (Coordinator)

```
1. Prepare canonical request:
   METHOD\n
   PATH\n
   TIMESTAMP\n
   NONCE\n
   SHA256(BODY)

2. Compute HMAC-SHA256:
   SIGNATURE = HMAC-SHA256(SECRET_KEY, CANONICAL_REQUEST)

3. Set headers:
   X-DS-Signature: <SIGNATURE>
   X-DS-Timestamp: <UNIX_TIMESTAMP>
   X-DS-Client-ID: coordinator
   X-DS-Nonce: <UNIQUE_UUID>
```

### Validation (Service)

```
1. Check header presence: SIGNATURE, TIMESTAMP, CLIENT_ID, NONCE
2. Validate timestamp: |NOW - TIMESTAMP| < MAX_AGE (300 seconds)
3. Check nonce uniqueness: Not in NonceStore
4. Get secret key based on CLIENT_ID:
   - "coordinator" → COORDINATOR_SECRET_KEY (write permissions)
   - "engineer" → ENGINEER_SECRET_KEY (read-only)
5. Compute expected signature with same canonical format
6. Constant-time compare: hmac.compare_digest(received, expected)
7. Store nonce for replay prevention
8. Enforce permission: reject writes for engineer key
```

### Signature Example

```python
import hashlib, hmac, time, json

method = "POST"
path = "/api/scan/start"
body = json.dumps({
    "organization_id": "org-123",
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-01-31T23:59:59Z"
})
timestamp = str(int(time.time()))
nonce = "550e8400-e29b-41d4-a716-446655440000"
secret = "coordinator-secret-key"

body_hash = hashlib.sha256(body.encode()).hexdigest()
canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()

headers = {
    "X-DS-Signature": signature,
    "X-DS-Timestamp": timestamp,
    "X-DS-Client-ID": "coordinator",
    "X-DS-Nonce": nonce
}
```

## Rate Limiting & Retry Strategy

### Rate Limit Detection

```
HTTP 429 Response:
  1. Parse `Retry-After` header (seconds or HTTP-date)
  2. Wait specified duration
  3. Retry same operation
  4. Continue if successful
  5. Log rate limit event to AuditLog
```

### Exponential Backoff (for other retryable errors)

```
Retryable errors: 502, 503, 504, TimeoutError, ConnectionError

Delay formula:
  delay = base_delay * (2 ^ attempt) + random(0, 1)
  
Example:
  Attempt 1: 1 * 2^0 + jitter = ~1 second
  Attempt 2: 1 * 2^1 + jitter = ~2 seconds
  Attempt 3: 1 * 2^2 + jitter = ~4 seconds
  Attempt 4: 1 * 2^3 + jitter = ~8 seconds
  Attempt 5: 1 * 2^4 + jitter = ~16 seconds
  
After 5 attempts exhausted:
  → Record to FailedExternalCall model
  → Update job status to FAILED
  → Log retry exhaustion event
```

## Data Normalization Schemas

### Envelopes Table

```json
{
  "envelope_id": "string (DocuSign envelope ID)",
  "status": "string (created, sent, delivered, completed, etc.)",
  "email_subject": "string",
  "created_at": "timestamp",
  "sent_at": "timestamp or null",
  "delivered_at": "timestamp or null",
  "completed_at": "timestamp or null",
  "expiration_date": "date or null",
  "custom_fields": "json"
}
```

### Recipients Table

```json
{
  "envelope_id": "string (foreign key)",
  "recipient_id": "string",
  "name": "string or null",
  "email": "string or null",
  "role": "string (signer, cc, bcc)",
  "type": "string (individual, company)",
  "status": "string (created, sent, delivered, completed, declined)",
  "signed_at": "timestamp or null",
  "declined_at": "timestamp or null"
}
```

### Documents Table

```json
{
  "envelope_id": "string (foreign key)",
  "document_id": "string",
  "name": "string",
  "type": "string (pdf, docx, etc.)",
  "file_extension": "string",
  "pages": "integer",
  "uri": "string (document URI)"
}
```

### Templates Table

```json
{
  "template_id": "string (DocuSign template ID)",
  "name": "string",
  "description": "string or null",
  "pages": "integer",
  "created_at": "timestamp",
  "updated_at": "timestamp",
  "owner_name": "string"
}
```

## MinIO Storage Layout

### Bucket Structure

```
docusign/
├── envelopes/
│   └── glynac_organization_id=org-123/
│       └── processing_date=2024-01-15/
│           ├── envelopes.parquet
│           └── envelopes.json
├── recipients/
│   └── glynac_organization_id=org-123/
│       └── processing_date=2024-01-15/
│           ├── recipients.parquet
│           └── recipients.json
├── documents/
│   └── glynac_organization_id=org-123/
│       └── processing_date=2024-01-15/
│           ├── documents.parquet
│           └── documents.json
└── templates/
    └── glynac_organization_id=org-123/
        └── processing_date=2024-01-15/
            ├── templates.parquet
            └── templates.json
```

### Key Pattern Formula

```
docusign/{table_name}/glynac_organization_id={organization_id}/processing_date={YYYY-MM-DD}/{table_name}.{format}
```

## Performance Considerations

### Database Indexes

```sql
-- Job queries by organization and status
CREATE INDEX idx_job_org_created ON job(organization_id, created_at DESC);
CREATE INDEX idx_job_status_heartbeat ON job(status, last_heartbeat) WHERE status IN ('FETCHING_ENVELOPES', 'FETCHING_DETAILS', 'NORMALIZING', 'UPLOADING_TO_MINIO');

-- Checkpoint lookups
CREATE INDEX idx_checkpoint_job ON job_checkpoint(job_id);

-- Audit logs
CREATE INDEX idx_audit_event_type_timestamp ON audit_log(event_type, timestamp DESC);
CREATE INDEX idx_audit_org_timestamp ON audit_log(organization_id, timestamp DESC);

-- Nonce replay protection
CREATE INDEX idx_nonce_created ON nonce_store(created_at);
```

### Pagination

- API returns max 100 items per page by default
- Uses offset/limit pagination
- Clients can request larger batches with `limit` parameter

### Checkpoint Granularity

- Save checkpoint after each envelope page (~100 envelopes per page)
- Save checkpoint after all details fetched for envelope
- Balance between recovery granularity and database load

## Security Considerations

### Secrets Management

- **Never** store DocuSign private keys in code or repositories
- Use environment variables for all secrets
- Rotate HMAC secrets regularly in production
- Audit logs never contain tokens, passwords, or private keys

### HMAC Security

- Use constant-time comparison to prevent timing attacks
- Rotate nonce generation with UUIDs
- Clean up old nonces (>24 hours) regularly
- Enforce read-only restrictions on engineer key

### Database Security

- All timestamps in UTC
- Foreign key constraints prevent orphaned data
- Unique constraints on job IDs and nonces
- Transaction safety for concurrent worker processes

### Error Handling

- Don't expose internal error details to clients
- Log full errors server-side for debugging
- Validate all input (organization IDs, date ranges, etc.)
- Sanitize metadata stored in FailedExternalCall

## Scalability

### Horizontal Scaling

```
+─────────────────────────────────────────────────┐
│           Load Balancer (Nginx/ALB)             │
└────┬─────────────────────┬────────────────────┬─┘
     │                     │                    │
     ▼                     ▼                    ▼
  ┌─────────┐          ┌─────────┐          ┌─────────┐
  │ Django  │          │ Django  │   ...    │ Django  │
  │ API #1  │          │ API #2  │          │ API #N  │
  └─────────┘          └─────────┘          └─────────┘
     │                     │                    │
     └─────────────────────┴────────────────────┘
                     │
                     ▼
            ┌─────────────────────┐
            │  PostgreSQL (RW)    │
            │  Read replicas      │
            └─────────────────────┘

+─────────────────────────────────────────────────┐
│              Worker Pool                        │
│  ┌──────────┐  ┌──────────┐      ┌──────────┐ │
│  │ Worker #1│  │ Worker #2│ ...  │ Worker #N│ │
│  └──────────┘  └──────────┘      └──────────┘ │
│       All with SELECT FOR UPDATE SKIP LOCKED   │
└─────────────────────────────────────────────────┘
                     │
                     ▼
            ┌─────────────────────┐
            │  PostgreSQL (RO)    │
            │  Transaction safety │
            └─────────────────────┘
```

### Concurrency Safety

- `SELECT FOR UPDATE SKIP LOCKED` ensures one worker per job
- No race conditions between API and workers
- Nonce replay protection prevents duplicate requests

## Monitoring & Observability

### Key Metrics

- Jobs by status distribution
- Average extraction time by organization
- Rate limit hit frequency
- Retry exhaustion rate
- Audit event frequency by type
- Database query performance

### Audit Trail

Every significant operation is logged with:
- Event type and timestamp
- Organization and client ID
- Job ID (if applicable)
- Outcome (SUCCESS/FAILURE)
- Relevant metadata (counts, errors, etc.)

Audit logs never contain sensitive data like:
- DocuSign access tokens
- HMAC secrets or signatures
- RSA private keys
- MinIO credentials
- Database passwords
