#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

free_port() {
  local port="${1:-8081}"
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
  fi
  sleep 1
}

echo "=== Running Aegis Webhook Ingestion Pipeline ==="
export PYTHONPATH="$ROOT_DIR"
export WEBHOOK_SECRET="test_secret_123"
export GITHUB_WEBHOOK_SECRET="test_secret_123"
export DATABASE_URL="sqlite:///./test_aegis.db"

free_port 8081

# Start the server in the background
echo "Starting FastAPI server in the background..."
.venv/bin/uvicorn backend.app.main:app --port 8081 &
SERVER_PID=$!

sleep 3
export AEGIS_API_URL="http://localhost:8081"
trap "echo 'Shutting down server...'; kill $SERVER_PID 2>/dev/null || true; free_port 8081" EXIT

.venv/bin/pytest backend/tests/blackbox/test_webhook_ingestion.py -v
