# Docker Network Connectivity Issues - Solutions

## Problem
Docker cannot reach Docker Hub to pull images (timeout errors).

## Root Causes
- Network connectivity issues
- Docker Hub DNS resolution problems
- Network firewall blocking Docker Hub

## Solutions

### Solution 1: Check Network Connectivity

```bash
# Check if you can reach Docker Hub
ping docker.io

# Check DNS resolution
nslookup docker.io
```

If these fail, you have network issues to resolve first.

### Solution 2: Configure Docker DNS

Edit or create `/etc/docker/daemon.json`:

```bash
sudo nano /etc/docker/daemon.json
```

Add or modify DNS settings:

```json
{
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
```

Restart Docker:

```bash
sudo systemctl restart docker
```

### Solution 3: Use Local Images (Quick Test)

If you just want to test the Django application without real database/storage, you can:

**Skip Docker Compose and test locally:**

```bash
cd "/home/simon/Downloads/DocuSign Master Service"
source venv/bin/activate

# Install core dependencies
pip install Django djangorestframework psycopg2-binary

# Run Django check
python manage.py check

# Start server
python manage.py runserver
```

Test health endpoint:
```bash
curl http://localhost:8000/api/health
```

### Solution 4: Retry with Exponential Backoff

Sometimes temporary network glitches resolve on retry:

```bash
cd "/home/simon/Downloads/DocuSign Master Service"

# Try pulling images with timeout
sudo docker-compose pull --no-parallel

# If that fails, try again after a minute
sleep 60
sudo docker-compose pull
```

### Solution 5: Configure Docker Hub Alternative Registry

If Docker Hub is blocked, use an alternative registry mirror:

**Edit `/etc/docker/daemon.json`:**

```json
{
  "registry-mirrors": [
    "https://docker.1panel.live",
    "https://hub.uuuadc.top",
    "https://docker.ckyl.me"
  ],
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

Restart Docker:

```bash
sudo systemctl restart docker
```

Then retry:

```bash
cd "/home/simon/Downloads/DocuSign Master Service"
sudo docker-compose pull
```

### Solution 6: Manually Pull Images

Try pulling individual images with more verbose output:

```bash
# Try pulling with specific retry
sudo docker pull --quiet postgres:15 || sudo docker pull postgres:15

sudo docker pull --quiet minio/minio:latest || sudo docker pull minio/minio:latest
```

### Solution 7: Use Docker without Pulling (If Images Already Cached)

If you previously had these images, Docker might have them cached:

```bash
cd "/home/simon/Downloads/DocuSign Master Service"

# Just start without pulling (assumes images already exist)
sudo docker-compose up -d
```

## Quick Check Commands

```bash
# Check Docker daemon status
sudo systemctl status docker

# Check Docker network connectivity
docker run --rm busybox ping -c 1 docker.io

# Check DNS from Docker
docker run --rm busybox nslookup docker.io

# List available images locally
docker images
```

## If Nothing Works: Local Development Alternative

Since the application is fully functional in Django, you can develop/test locally:

```bash
cd "/home/simon/Downloads/DocuSign Master Service"

# Activate venv
source venv/bin/activate

# Install minimal requirements
pip install Django==4.2.8 djangorestframework==3.14.0

# Run migrations (uses SQLite by default)
python manage.py migrate

# Start server
python manage.py runserver

# In another terminal, test the API
curl http://localhost:8000/api/health
```

This gives you full access to:
- All REST API endpoints
- Job management
- Audit logging
- Health checks

The only limitation is no separate PostgreSQL/MinIO (they use SQLite/local file storage instead).

## Contact Your ISP/Network Admin

If these solutions don't work:
- Your network may be filtering Docker registry traffic
- Contact your network administrator
- Request unblocking of registry.docker.io, docker.io, quay.io
- Request DNS access to 8.8.8.8 (Google DNS)

## After Fixing Network Issues

Once your network is fixed, retry:

```bash
cd "/home/simon/Downloads/DocuSign Master Service"
sudo docker-compose pull
sudo docker-compose up -d
curl http://localhost:8000/api/health
```
