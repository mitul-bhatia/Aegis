#!/bin/bash

echo "🛡️ Starting Aegis Services..."

# Start Backend
echo "📡 Starting Backend Server..."
cd "$(dirname "$0")"
source .venv/bin/activate
python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start Frontend
echo "🌐 Starting Frontend Server..."
cd "$(dirname "$0")/aegis-frontend"
npm run dev &
FRONTEND_PID=$!

echo "✅ Services Started!"
echo "🔗 Backend: http://localhost:8000"
echo "🔗 Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
