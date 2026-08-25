#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== Starting Aegis 2.0 Backend on http://localhost:8000 ==="
export PYTHONPATH="$ROOT_DIR"
.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
