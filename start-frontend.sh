#!/bin/bash
# Aegis Frontend Starter
# Kills any process on port 3000 and starts the Next.js frontend

echo "🎨 Starting Aegis Frontend..."

# Kill any process on port 3000
echo "Checking for processes on port 3000..."
lsof -ti:3000 | xargs kill -9 2>/dev/null && echo "✓ Killed existing process on port 3000" || echo "✓ Port 3000 is free"

# Navigate to frontend directory and start
echo "Starting Next.js dev server..."
cd aegis-frontend
npm run dev
