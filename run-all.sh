#!/usr/bin/env bash
set -e

# ==============================================================================
# Aegis 2.0 — Start Everything (Backend + Frontend)
# ==============================================================================

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo -e "${CYAN}"
echo "    ___    ______ _____ _____ _____ "
echo "   /   |  / ____// ___// ___// ___/ "
echo "  / /| | / __/  / / _  \__ \ \__ \  "
echo " / ___ |/ /___ / /_/ / ___/ /___/ / "
echo "/_/  |_/_____/ \____/ /____//____/  "
echo "   >> AUTONOMOUS SECURITY PLATFORM <<"
echo -e "${NC}"

# Cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}[*] Shutting down Aegis services...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend
echo -e "${GREEN}[1/2] Starting FastAPI Backend on http://localhost:8000 ...${NC}"
export PYTHONPATH="$ROOT_DIR"
.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# 2. Start Frontend
echo -e "${GREEN}[2/2] Starting Next.js Frontend on http://localhost:3000 ...${NC}"
cd "$ROOT_DIR/aegis-frontend"
export NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev -- -p 3000 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "🚀 ${CYAN}Aegis 2.0 Full Stack is Running!${NC}"
echo -e "🌐 Web Dashboard:    ${GREEN}http://localhost:3000${NC}"
echo -e "⚙️  Backend API:       ${GREEN}http://localhost:8000${NC}"
echo -e "📚 Interactive Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "${YELLOW}Press [Ctrl+C] anytime to stop all services.${NC}\n"

wait
