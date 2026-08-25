#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== Running Aegis 2.0 End-to-End Test Suite ==="
export PYTHONPATH="$ROOT_DIR"
.venv/bin/python backend/tests/test_e2e_pipeline.py
