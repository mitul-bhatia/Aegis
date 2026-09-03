#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=== Running Aegis Sandbox Isolation Pipeline ==="
export PYTHONPATH="$ROOT_DIR"

.venv/bin/pytest backend/tests/blackbox/test_sandbox_isolation.py -v
