#!/bin/bash
# Aegis — Start All Services (Backend + Frontend)
# Usage: ./start-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🛡️  Starting Aegis Services..."

# Kill any process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Start Backend
echo "📡 Starting Backend (FastAPI)..."
cd "$SCRIPT_DIR"
source .venv/bin/activate
python main.py &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3

# Start Frontend
echo "🌐 Starting Frontend (Next.js)..."
cd "$SCRIPT_DIR/aegis-frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Services Started!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Graceful shutdown on Ctrl+C
trap "echo '🛑 Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
