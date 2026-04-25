#!/bin/bash
# Aegis Backend Starter
# Kills any process on port 8000 and starts the FastAPI backend

echo "🛡️  Starting Aegis Backend..."

# Kill any process on port 8000
echo "Checking for processes on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null && echo "✓ Killed existing process on port 8000" || echo "✓ Port 8000 is free"

# Activate virtual environment and start backend
echo "Starting FastAPI server..."
source .venv/bin/activate
python main.py
