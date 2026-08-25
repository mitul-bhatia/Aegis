#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR/aegis-frontend"

echo "=== Starting Aegis 2.0 Frontend on http://localhost:3000 ==="
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev -- -p 3000
