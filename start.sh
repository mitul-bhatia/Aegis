#!/usr/bin/env bash
set -e

echo "=== Starting Aegis 2.0 Backend ==="
export PYTHONPATH=.
.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
