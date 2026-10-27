#!/usr/bin/env python3
"""
Generate HMAC secret keys for DocuSign Master Service

Usage:
    python generate_hmac_secrets.py
"""

import secrets
import sys


def generate_secrets():
    """Generate random HMAC secret keys"""
    
    # Generate 32-byte (256-bit) random keys
    coordinator_key = secrets.token_hex(32)
    engineer_key = secrets.token_hex(32)
    
    print("\n" + "="*80)
    print("DocuSign Master Service - HMAC Secret Generation")
    print("="*80 + "\n")
    
    print("🔐 Copy these values to your .env file:\n")
    
    print("# Coordinator key (write permissions)")
    print(f"HMAC_SECRET_KEY_CORE={coordinator_key}\n")
    
    print("# Engineer key (read-only access)")
    print(f"HMAC_SECRET_KEY_ENGINEER={engineer_key}\n")
    
    print("# Keep these as-is (no changes needed)")
    print("HMAC_SIGNATURE_MAX_AGE=300")
    print("HMAC_CLIENT_CONFIG=coordinator,engineer\n")
    
    print("="*80)
    print("⚠️  IMPORTANT: Never commit these values to Git!")
    print("   Keep them in .env file only (not in .env.example)")
    print("="*80 + "\n")
    
    return {
        'coordinator': coordinator_key,
        'engineer': engineer_key,
        'max_age': 300,
        'clients': 'coordinator,engineer'
    }


def print_usage_example(creds):
    """Print example of how to use these keys"""
    
    print("\n" + "="*80)
    print("Example: Using These Keys with the API")
    print("="*80 + "\n")
    
    print("1. From Python (Coordinator creates signed request):\n")
    
    example_python = f'''import hashlib
import hmac
import time

method = "POST"
path = "/api/scan/start"
body = '{{"organization_id":"org-123","date_from":"2024-01-01T00:00:00Z","date_to":"2024-01-31T23:59:59Z"}}'
timestamp = str(int(time.time()))
nonce = "unique-nonce-123"
secret = "{creds['coordinator']}"

# Compute signature
body_hash = hashlib.sha256(body.encode()).hexdigest()
canonical = f"{{method}}\\n{{path}}\\n{{timestamp}}\\n{{nonce}}\\n{{body_hash}}"
signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()

# Use in request headers:
headers = {{
    "X-DS-Signature": signature,
    "X-DS-Timestamp": timestamp,
    "X-DS-Client-ID": "coordinator",
    "X-DS-Nonce": nonce,
}}'''
    
    print(example_python)
    
    print("\n2. From Bash (using curl):\n")
    
    example_bash = f'''#!/bin/bash
TIMESTAMP=$(date +%s)
NONCE="test-nonce-$TIMESTAMP"
BODY='{{"organization_id":"org-123","date_from":"2024-01-01T00:00:00Z","date_to":"2024-01-31T23:59:59Z"}}'
SECRET="{creds['coordinator']}"

BODY_HASH=$(echo -n "$BODY" | sha256sum | awk '{{print $1}}')
CANONICAL="POST
/api/scan/start
$TIMESTAMP
$NONCE
$BODY_HASH"

SIGNATURE=$(echo -n "$CANONICAL" | openssl dgst -sha256 -hmac "$SECRET" | awk '{{print $2}}')

curl -X POST http://localhost:8000/api/scan/start \\
  -H "Content-Type: application/json" \\
  -H "X-DS-Signature: $SIGNATURE" \\
  -H "X-DS-Timestamp: $TIMESTAMP" \\
  -H "X-DS-Client-ID: coordinator" \\
  -H "X-DS-Nonce: $NONCE" \\
  -d "$BODY"'''
    
    print(example_bash)
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    try:
        creds = generate_secrets()
        print_usage_example(creds)
        
        print("✅ Secret keys generated successfully!")
        print("\n📝 Next steps:")
        print("   1. Copy the HMAC_SECRET_KEY_* values above")
        print("   2. Open .env file (cd to project, then: nano .env)")
        print("   3. Paste the values into the HMAC section")
        print("   4. Save and close (Ctrl+X, then Y, then Enter)")
        print("   5. Restart your Django server")
        print("   6. Test with the examples above\n")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
