#!/bin/bash

# Load environment variables
cd /home/simon/Downloads/DocuSign\ Master\ Service
source venv/bin/activate
source .env 2>/dev/null || echo "Warning: .env not found"

# Get the HMAC secrets (set defaults if not in .env)
COORDINATOR_SECRET="${HMAC_SECRET_KEY_CORE:-1e6436677f139cad7d6d3b2654b1dcd7ad6f8252ea4d9b133fe86c8d13aa170b}"
ENGINEER_SECRET="${HMAC_SECRET_KEY_ENGINEER:-16483765f1ffc1afa945961505879d87d06395911237aa42ebba8ca61c538b41}"

# API endpoint to test
API_ENDPOINT="http://localhost:8000/api/stats"

# Current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create the signature base string
SIGNATURE_BASE="${TIMESTAMP}"

# Generate HMAC-SHA256 signature (using coordinator secret for demo)
SIGNATURE=$(echo -n "$SIGNATURE_BASE" | openssl dgst -sha256 -hmac "$COORDINATOR_SECRET" -hex | cut -d' ' -f2)

echo "=== HMAC Authentication Test ==="
echo "Timestamp: $TIMESTAMP"
echo "Coordinator Secret (first 16 chars): ${COORDINATOR_SECRET:0:16}..."
echo "Signature: $SIGNATURE"
echo ""
echo "Making request to: $API_ENDPOINT"
echo ""

# Make the request with HMAC headers
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "X-Timestamp: $TIMESTAMP" \
  -H "X-Signature: $SIGNATURE" \
  -H "X-Client: coordinator" \
  -H "Content-Type: application/json" \
  "$API_ENDPOINT" | python -m json.tool 2>/dev/null || curl -s "$API_ENDPOINT"

echo ""
