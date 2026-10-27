# DocuSign Master Service - Quick Start Guide

## ⚡ 5-Minute Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 12+ (or use Docker)
- Docker & Docker Compose (recommended)

### Option 1: Docker Compose (Fastest)

```bash
# 1. Navigate to project directory
cd "/home/simon/Downloads/DocuSign Master Service"

# 2. Configure environment
cp .env.example .env
# Edit .env with your DocuSign credentials and HMAC secrets

# 3. Start all services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f django-app

# 6. Test the service
curl http://localhost:8000/api/health

# 7. Access MinIO console
# Open browser: http://localhost:9001 (user: minioadmin, pass: minioadmin)
```

### Option 2: Local Development

```bash
# 1. Navigate to project
cd "/home/simon/Downloads/DocuSign Master Service"

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies (if not already done)
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your DocuSign credentials

# 5. Setup database (PostgreSQL must be running)
python manage.py migrate

# 6. Start Django server (Terminal 1)
python manage.py runserver

# 7. Start worker (Terminal 2)
python manage.py run_scan_worker

# 8. Test
curl http://localhost:8000/api/health
```

## 🧪 Testing the API

### 1. Health Check (No Auth Required)

```bash
curl http://localhost:8000/api/health
```

### 2. Generate HMAC Signature

```python
import hashlib
import hmac
import time
import json

method = "POST"
path = "/api/scan/start"
body = json.dumps({
    "organization_id": "test-org",
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-01-31T23:59:59Z"
})
timestamp = str(int(time.time()))
nonce = "test-nonce-" + str(int(time.time() * 1000))
secret = "your_coordinator_secret_key"  # from .env

# Compute signature
body_hash = hashlib.sha256(body.encode()).hexdigest()
canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()

print(f"Signature: {signature}")
print(f"Timestamp: {timestamp}")
print(f"Nonce: {nonce}")
```

### 3. Create Extraction Job

```bash
SIGNATURE="<computed-signature>"
TIMESTAMP="<current-timestamp>"
NONCE="<unique-nonce>"

curl -X POST http://localhost:8000/api/scan/start \
  -H "Content-Type: application/json" \
  -H "X-DS-Signature: $SIGNATURE" \
  -H "X-DS-Timestamp: $TIMESTAMP" \
  -H "X-DS-Client-ID: coordinator" \
  -H "X-DS-Nonce: $NONCE" \
  -d '{
    "organization_id": "test-org",
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-01-31T23:59:59Z"
  }'
```

### 4. Check Job Status

```bash
curl http://localhost:8000/api/scan/{scan_id}/status
```

### 5. List All Jobs

```bash
curl "http://localhost:8000/api/scan/list?organization_id=test-org&limit=10"
```

## 📊 Monitoring

### View Logs (Docker)

```bash
# API server
docker-compose logs -f django-app

# Background worker
docker-compose logs -f worker

# All services
docker-compose logs -f
```

### View Logs (Local)

Logs are written to:
```
logs/django.log
```

### Check Database

```bash
# Docker
docker-compose exec db psql -U docusign_user -d docusign_db

# Local (if PostgreSQL installed)
psql -U docusign_user -d docusign_db
```

### Audit Trail

```bash
# Get recent audit events
curl "http://localhost:8000/api/audit/logs?limit=50"
```

## 🔧 Troubleshooting

### "Connection refused" for PostgreSQL

```bash
# Ensure PostgreSQL is running
docker-compose ps postgres

# If not running, start it
docker-compose up -d postgres
```

### "Cannot connect to MinIO"

```bash
# Check MinIO service
docker-compose ps minio

# If failed, restart
docker-compose restart minio
```

### "HMAC signature validation failed"

1. Verify timestamp is current (within 5 minutes)
2. Check nonce is unique
3. Ensure you're using correct secret key
4. Verify signature computation: METHOD\nPATH\nTIMESTAMP\nNONCE\nSHA256(BODY)

### "Job not found"

1. Verify scan_id is correct
2. Check job was created successfully (got 202 response)
3. List jobs: `GET /api/scan/list`

## 🛑 Stopping Services

### Docker

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Local

```bash
# Stop worker (Ctrl+C in terminal)
# Stop Django server (Ctrl+C in terminal)
```

## 📚 Next Steps

1. **Read Full Documentation**: See [README.md](README.md)
2. **Understand Architecture**: See [DESIGN.md](DESIGN.md)
3. **Configure DocuSign**: Get real credentials from [DocuSign Developer](https://developer.docusign.com/)
4. **Run Tests**: `pytest tests/ -v`
5. **Deploy to Production**: Configure env vars and use Docker Compose in production

## 🆘 Getting Help

### Common Issues

| Issue | Solution |
|-------|----------|
| Port 8000 already in use | Change in docker-compose.yml or use different port |
| PostgreSQL authentication failed | Check DATABASE_URL in .env |
| MinIO bucket not found | Set MINIO_BUCKET_NAME in .env |
| HMAC always fails | Ensure secret keys are configured in .env |
| Worker not processing jobs | Check PENDING jobs exist, worker is running |

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python manage.py run_scan_worker --verbosity 3
```

## ✅ Verification Checklist

- [ ] Docker Compose up: `docker-compose ps` shows all containers running
- [ ] Health check passes: `curl http://localhost:8000/api/health`
- [ ] Database migrated: Check no pending migrations
- [ ] Worker started: Check logs for "Starting DocuSign extraction worker"
- [ ] Can create job: POST request returns 202
- [ ] Job processed: Status changes from PENDING to other stages
- [ ] Audit logs recorded: Check `/api/audit/logs`

## 🚀 You're Ready!

The DocuSign Master Service is fully configured and ready to extract data.

Start with:
```bash
docker-compose up -d
curl http://localhost:8000/api/health
```

Then create your first job and watch it process!
