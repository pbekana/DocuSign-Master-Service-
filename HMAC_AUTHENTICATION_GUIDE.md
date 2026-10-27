# HMAC Authentication Configuration Guide

## Overview

HMAC (Hash-based Message Authentication Code) is used to secure communication between the Coordinator system and the DocuSign Master Service. The Coordinator signs requests with a secret key, and the Service validates those signatures.

## Configuration Values Explained

### 1. `HMAC_SECRET_KEY_CORE` (Coordinator Key)

**What it is**: The secret key used by the Coordinator to sign requests with write permissions.

**Where to get it**: **You generate it yourself**. This is not provided by any external service.

**How to generate** (choose one method):

#### Method A: Using Python (Recommended)
```python
import secrets
import base64

# Generate a 32-byte random key (256-bit security)
secret_key = secrets.token_bytes(32)
secret_key_hex = secret_key.hex()
print(f"HMAC_SECRET_KEY_CORE={secret_key_hex}")
```

**Output example**:
```
HMAC_SECRET_KEY_CORE=a7f3b2e8c5d9f1a4b6c8e0f3a5b7d9e1c3f5a7b9d1e3f5a7b9c1d3e5f7a9b
```

#### Method B: Using OpenSSL
```bash
openssl rand -hex 32
```

**Output example**:
```
7a9c3f5e1b8d6a2c4e9f1b3d5a7c9e1f3b5d7a9c1e3f5a7b9d1e3f5a7b9c1
```

#### Method C: Using Linux /dev/urandom
```bash
head -c 32 /dev/urandom | xxd -p
```

**Output example**:
```
f3a5b7d9e1c3f5a7b9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a
```

---

### 2. `HMAC_SECRET_KEY_ENGINEER` (Engineer Read-Only Key)

**What it is**: A separate secret key for read-only inspection access (lower privileges).

**Where to get it**: **You generate it yourself**, just like the coordinator key.

**Why separate keys?** 
- Coordinator key can create, delete, and modify jobs (write operations)
- Engineer key can only view jobs and logs (read-only)
- If engineer key is compromised, damage is limited

**How to generate** (same methods as coordinator key):

```python
import secrets
secret_key = secrets.token_bytes(32)
print(f"HMAC_SECRET_KEY_ENGINEER={secret_key.hex()}")
```

**Output example**:
```
HMAC_SECRET_KEY_ENGINEER=e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7
```

---

### 3. `HMAC_SIGNATURE_MAX_AGE`

**What it is**: Maximum age of a request signature in seconds.

**Where to get it**: This is a policy you set, not something to retrieve.

**Default value**: `300` (5 minutes)

**Why 5 minutes?**
- Prevents replay attacks of old signatures
- Allows for reasonable clock skew between client and server
- Balances security and usability

**When to change**:
- Increase if your network has high latency
- Decrease if you need stricter security

**Example values**:
```env
HMAC_SIGNATURE_MAX_AGE=60      # 1 minute (strict)
HMAC_SIGNATURE_MAX_AGE=300     # 5 minutes (default, balanced)
HMAC_SIGNATURE_MAX_AGE=600     # 10 minutes (lenient)
```

**Keep the default** (300) unless you have a specific reason to change it.

---

### 4. `HMAC_CLIENT_CONFIG`

**What it is**: List of client IDs that are allowed to authenticate.

**Where to get it**: You define this based on your system design.

**Default value**: `coordinator,engineer`

**Explanation**:
- `coordinator` - Client that creates and manages jobs
- `engineer` - Client that inspects jobs and logs (read-only)

**How it's used in code**:
```python
# In requests, client identifies itself with header:
X-DS-Client-ID: coordinator  # or engineer

# Service checks if client ID is in HMAC_CLIENT_CONFIG
if client_id in ["coordinator", "engineer"]:
    # Valid client
    if client_id == "coordinator":
        secret = HMAC_SECRET_KEY_CORE
        permission_level = "write"
    elif client_id == "engineer":
        secret = HMAC_SECRET_KEY_ENGINEER
        permission_level = "read-only"
```

**If you want to add more clients**:
```env
HMAC_CLIENT_CONFIG=coordinator,engineer,admin,analyst
```

**Keep the default** unless you need additional client types.

---

## Complete Configuration Example

Here's what to put in your `.env` file:

```env
# Generate these using the methods above

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
HMAC_SECRET_KEY_CORE=a7f3b2e8c5d9f1a4b6c8e0f3a5b7d9e1c3f5a7b9d1e3f5a7b9c1d3e5f7a9b

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
HMAC_SECRET_KEY_ENGINEER=e9f1a3b5c7d9e1f3a5b7c9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7

# Keep at 300 (5 minutes) for most use cases
HMAC_SIGNATURE_MAX_AGE=300

# These are the allowed client IDs - keep as is
HMAC_CLIENT_CONFIG=coordinator,engineer
```

---

## How to Generate: Step-by-Step

### Using Python (Easy)

```bash
# Open Python interpreter
python3

# Then run:
import secrets
print("HMAC_SECRET_KEY_CORE=" + secrets.token_hex(32))
print("HMAC_SECRET_KEY_ENGINEER=" + secrets.token_hex(32))

# Exit
exit()
```

**Output**:
```
HMAC_SECRET_KEY_CORE=7a9c3f5e1b8d6a2c4e9f1b3d5a7c9e1f3b5d7a9c1e3f5a7b9d1e3f5a7b9c1
HMAC_SECRET_KEY_ENGINEER=f3a5b7d9e1c3f5a7b9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a3
```

### Using Bash (Quick)

```bash
# Generate coordinator key
openssl rand -hex 32

# Generate engineer key
openssl rand -hex 32
```

---

## Where These Are Used

### In Your Django Application

**File**: `config/settings.py`
```python
HMAC_ENABLED = True
HMAC_SECRET_KEY_CORE = os.getenv('HMAC_SECRET_KEY_CORE')
HMAC_SECRET_KEY_ENGINEER = os.getenv('HMAC_SECRET_KEY_ENGINEER')
HMAC_SIGNATURE_MAX_AGE = int(os.getenv('HMAC_SIGNATURE_MAX_AGE', '300'))
```

**File**: `apps/authentication/middleware.py`
```python
# Validates incoming requests
# Extracts signature from X-DS-Signature header
# Computes expected signature using secret key
# Compares with constant-time comparison
```

---

## How the Coordinator Uses These Keys

### Step 1: Generate Signature

The Coordinator (your external system) must generate a signature:

```python
import hashlib
import hmac
import time

def sign_request(method, path, body, secret_key):
    """Generate HMAC-SHA256 signature for a request"""
    
    timestamp = str(int(time.time()))
    nonce = "unique-nonce-" + str(int(time.time() * 1000))
    
    # Compute body hash
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    
    # Build canonical string
    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    
    # Compute HMAC-SHA256
    signature = hmac.new(
        secret_key.encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature, timestamp, nonce

# Example usage:
method = "POST"
path = "/api/scan/start"
body = '{"organization_id":"org-123","date_from":"2024-01-01T00:00:00Z","date_to":"2024-01-31T23:59:59Z"}'
secret = "a7f3b2e8c5d9f1a4b6c8e0f3a5b7d9e1c3f5a7b9d1e3f5a7b9c1d3e5f7a9b"

sig, ts, nonce = sign_request(method, path, body, secret)
print(f"X-DS-Signature: {sig}")
print(f"X-DS-Timestamp: {ts}")
print(f"X-DS-Nonce: {nonce}")
```

### Step 2: Send Request with Headers

```bash
curl -X POST http://localhost:8000/api/scan/start \
  -H "Content-Type: application/json" \
  -H "X-DS-Signature: <computed-signature>" \
  -H "X-DS-Timestamp: <timestamp>" \
  -H "X-DS-Client-ID: coordinator" \
  -H "X-DS-Nonce: <unique-nonce>" \
  -d '{"organization_id":"org-123","date_from":"2024-01-01T00:00:00Z","date_to":"2024-01-31T23:59:59Z"}'
```

### Step 3: Service Validates

The Django service will:
1. Extract headers
2. Check timestamp is within 5 minutes (HMAC_SIGNATURE_MAX_AGE)
3. Check nonce hasn't been used before (replay protection)
4. Get secret key based on client ID
5. Recompute expected signature
6. Compare with constant-time comparison
7. Accept or reject request

---

## Security Best Practices

### ✅ DO

- ✅ Generate unique secrets for coordinator and engineer
- ✅ Keep secret keys in `.env` file (never commit to Git)
- ✅ Rotate secrets periodically (annually or after compromise)
- ✅ Use 32-byte (256-bit) keys minimum
- ✅ Store secrets in environment variables or secure vault
- ✅ Keep HMAC_SIGNATURE_MAX_AGE at 300 or less
- ✅ Use HTTPS in production

### ❌ DON'T

- ❌ Use simple passwords or sequential numbers
- ❌ Commit `.env` file to Git
- ❌ Share secret keys via email or chat
- ❌ Use same key for coordinator and engineer
- ❌ Log or display secret keys
- ❌ Set HMAC_SIGNATURE_MAX_AGE too high (>3600)
- ❌ Use HTTP in production

---

## Example: Complete .env Setup

```env
# HMAC Authentication Configuration
# Generate these with: python -c "import secrets; print(secrets.token_hex(32))"

# Secret key for Coordinator client (can write/modify/delete)
HMAC_SECRET_KEY_CORE=7a9c3f5e1b8d6a2c4e9f1b3d5a7c9e1f3b5d7a9c1e3f5a7b9d1e3f5a7b9c1

# Secret key for Engineer client (read-only, inspection only)
HMAC_SECRET_KEY_ENGINEER=f3a5b7d9e1c3f5a7b9d1e3f5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a3

# Maximum age of request signature in seconds (300 = 5 minutes)
HMAC_SIGNATURE_MAX_AGE=300

# Allowed client IDs (comma-separated)
HMAC_CLIENT_CONFIG=coordinator,engineer
```

---

## Testing Your HMAC Setup

### 1. Test with Python Script

```python
#!/usr/bin/env python3
import hashlib
import hmac
import time
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
COORDINATOR_SECRET = "7a9c3f5e1b8d6a2c4e9f1b3d5a7c9e1f3b5d7a9c1e3f5a7b9d1e3f5a7b9c1"
CLIENT_ID = "coordinator"

def sign_request(method, path, body, secret):
    timestamp = str(int(time.time()))
    nonce = f"test-nonce-{int(time.time() * 1000)}"
    
    body_bytes = body.encode() if isinstance(body, str) else body
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    
    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    
    signature = hmac.new(
        secret.encode(),
        canonical.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return signature, timestamp, nonce

# Test creating a job
path = "/api/scan/start"
method = "POST"
body = json.dumps({
    "organization_id": "test-org",
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-01-31T23:59:59Z"
})

signature, timestamp, nonce = sign_request(method, path, body, COORDINATOR_SECRET)

headers = {
    "Content-Type": "application/json",
    "X-DS-Signature": signature,
    "X-DS-Timestamp": timestamp,
    "X-DS-Client-ID": CLIENT_ID,
    "X-DS-Nonce": nonce,
}

response = requests.post(f"{BASE_URL}{path}", data=body, headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

### 2. Test with curl

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"
SECRET="7a9c3f5e1b8d6a2c4e9f1b3d5a7c9e1f3b5d7a9c1e3f5a7b9d1e3f5a7b9c1"
PATH="/api/scan/start"
TIMESTAMP=$(date +%s)
NONCE="test-nonce-$(date +%s%N)"

BODY='{"organization_id":"test-org","date_from":"2024-01-01T00:00:00Z","date_to":"2024-01-31T23:59:59Z"}'

BODY_HASH=$(echo -n "$BODY" | sha256sum | awk '{print $1}')

CANONICAL="POST
$PATH
$TIMESTAMP
$NONCE
$BODY_HASH"

SIGNATURE=$(echo -n "$CANONICAL" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

curl -X POST "$BASE_URL$PATH" \
  -H "Content-Type: application/json" \
  -H "X-DS-Signature: $SIGNATURE" \
  -H "X-DS-Timestamp: $TIMESTAMP" \
  -H "X-DS-Client-ID: coordinator" \
  -H "X-DS-Nonce: $NONCE" \
  -d "$BODY"
```

---

## Summary

| Config | Generate? | How | Example |
|--------|-----------|-----|---------|
| `HMAC_SECRET_KEY_CORE` | YES | `python -c "import secrets; print(secrets.token_hex(32))"` | `7a9c3f5e1b8d...` |
| `HMAC_SECRET_KEY_ENGINEER` | YES | `python -c "import secrets; print(secrets.token_hex(32))"` | `f3a5b7d9e1c3...` |
| `HMAC_SIGNATURE_MAX_AGE` | NO | Use `300` | `300` |
| `HMAC_CLIENT_CONFIG` | NO | Use default | `coordinator,engineer` |

**Next Step**: Generate your secrets and update `.env` file!
