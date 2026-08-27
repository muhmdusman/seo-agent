#!/bin/bash

# Search Console Agent - Full Stack Development Startup
# This script starts database, backend, and frontend with a single command

set -e

echo "🚀 Starting Search Console Agent (Full Stack)"
echo "═══════════════════════════════════════════════"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "   Please create .env file with required variables"
    exit 1
fi

# Start backend (database + API)
echo "🔧 Starting Backend..."
cd backend

# Create symlink to .env
ln -sfn ../.env .env 2>/dev/null || true

# Start PostgreSQL
docker compose -f db/docker-compose.yaml up -d
sleep 3

# Run migrations
uv run alembic upgrade head 2>/dev/null || echo "Migrations already up to date"

# Start backend in background
echo "   Starting FastAPI..."
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo ""
echo "🌐 Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

cd ..

# Display URLs
echo ""
echo "✅ All services started!"
echo "═══════════════════════════════════════════════"
echo ""
echo "📍 Application URLs:"
echo "   🌐 Frontend:  http://localhost:3000"
echo "   🔧 Backend:   http://127.0.0.1:8000"
echo "   📖 API Docs:  http://127.0.0.1:8000/docs"
echo "   🗄️  Adminer:   http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop all services"
echo "═══════════════════════════════════════════════"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping all services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; cd backend && docker compose -f db/docker-compose.yaml down; echo '✅ All services stopped!'; exit 0" INT

# Keep script running
wait
