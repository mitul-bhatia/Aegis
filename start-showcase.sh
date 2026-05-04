#!/bin/bash

# Aegis Local Showcase Startup Script
# Starts all services needed for a demo

set -e

echo "🎯 Starting Aegis Showcase Environment..."
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
echo -e "${BLUE}[1/6]${NC} Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi
echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Check if sandbox image exists
echo -e "${BLUE}[2/6]${NC} Checking sandbox image..."
if ! docker images | grep -q aegis-sandbox; then
    echo -e "${YELLOW}⚠️  Sandbox image not found. Building...${NC}"
    ./build-sandbox.sh
fi
echo -e "${GREEN}✅ Sandbox image ready${NC}"
echo ""

# Check if virtual environment exists
echo -e "${BLUE}[3/6]${NC} Checking Python environment..."
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi
echo -e "${GREEN}✅ Python environment ready${NC}"
echo ""

# Check if frontend dependencies are installed
echo -e "${BLUE}[4/6]${NC} Checking frontend dependencies..."
if [ ! -d "aegis-frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠️  Frontend dependencies not found. Installing...${NC}"
    cd aegis-frontend
    npm install
    cd ..
fi
echo -e "${GREEN}✅ Frontend dependencies ready${NC}"
echo ""

# Initialize database
echo -e "${BLUE}[5/6]${NC} Initializing database..."
python -c "from database.db import init_db; init_db()" 2>/dev/null || true
echo -e "${GREEN}✅ Database initialized${NC}"
echo ""

# Check API keys
echo -e "${BLUE}[6/6]${NC} Checking API keys..."
if ! grep -q "MISTRAL_API_KEY=.*[a-zA-Z0-9]" .env; then
    echo -e "${RED}❌ MISTRAL_API_KEY not set in .env${NC}"
    exit 1
fi
if ! grep -q "GROQ_API_KEY=.*[a-zA-Z0-9]" .env; then
    echo -e "${RED}❌ GROQ_API_KEY not set in .env${NC}"
    exit 1
fi
echo -e "${GREEN}✅ API keys configured${NC}"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ All checks passed! Starting services...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Start backend in background
echo -e "${BLUE}Starting backend...${NC}"
python main.py > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
echo "   Logs: tail -f backend.log"
echo ""

# Wait for backend to be ready
echo -e "${BLUE}Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start${NC}"
        echo "Check backend.log for errors"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done
echo ""

# Start frontend in background
echo -e "${BLUE}Starting frontend...${NC}"
cd aegis-frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
echo "   Logs: tail -f frontend.log"
echo ""

# Wait for frontend to be ready
echo -e "${BLUE}Waiting for frontend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Frontend failed to start${NC}"
        echo "Check frontend.log for errors"
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done
echo ""

# Save PIDs for cleanup
echo "$BACKEND_PID" > .backend.pid
echo "$FRONTEND_PID" > .frontend.pid

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Aegis is ready for showcase!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📍 URLs:${NC}"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   Health:    http://localhost:8000/health"
echo ""
echo -e "${BLUE}📊 System Status:${NC}"
curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "   (Run 'curl http://localhost:8000/health' to check)"
echo ""
echo -e "${BLUE}📝 Next Steps:${NC}"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Add a repository (e.g., Jivit87/aegis-pr-test)"
echo "   3. Trigger a scan and watch the magic! ✨"
echo ""
echo -e "${YELLOW}⚠️  To stop all services, run:${NC}"
echo "   ./stop-showcase.sh"
echo ""
echo -e "${BLUE}📚 Demo Guide:${NC}"
echo "   cat LOCAL_SHOWCASE_GUIDE.md"
echo ""
