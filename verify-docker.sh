#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

SCAN_ID="${1:-1}"
API_URL="${2:-http://localhost:8000}"

echo "=== Running Local Docker Sandbox Exploit Verification for Scan #$SCAN_ID ==="
export PYTHONPATH="$ROOT_DIR"
.venv/bin/python backend/runner/aegis_cli.py verify "$SCAN_ID" --api-url "$API_URL"
