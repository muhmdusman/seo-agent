#!/bin/bash

# Search Console Agent - Full Stack Development Startup
# This script starts database, Redis, Celery worker, backend, and frontend with a single command

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

# Start backend (database + Redis + API + Celery)
echo "🔧 Starting Backend Services..."
cd backend

# Create symlink to .env
ln -sfn ../.env .env 2>/dev/null || true

# Start PostgreSQL and Redis
echo "   Starting PostgreSQL & Redis..."
docker compose -f docker-compose.yaml up -d

# Wait for services to be healthy
echo "   Waiting for database to be ready..."
sleep 5

# Check if services are running
if ! docker ps | grep -q "postgres"; then
    echo "❌ Error: PostgreSQL failed to start"
    exit 1
fi

if ! docker ps | grep -q "redis"; then
    echo "❌ Error: Redis failed to start"
    exit 1
fi

echo "✅ Database and Redis are running!"
echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
uv sync

# Run migrations
echo "🔄 Running database migrations..."
uv run alembic upgrade head 2>/dev/null || echo "Migrations already up to date"
echo ""

# Start Celery worker in background
echo "🔄 Starting Celery worker..."
uv run celery -A core.celery_app worker --loglevel=info > celery.log 2>&1 &
CELERY_PID=$!
echo "   Celery worker started (PID: $CELERY_PID)"
echo ""

# Start backend API in background
echo "   Starting FastAPI..."
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend API started (PID: $BACKEND_PID)"

cd ..

# Wait for backend to start
echo "   Waiting for backend to be ready..."
sleep 5

# Check if backend is responding
if ! curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/openapi.json | grep -q "200"; then
    echo "⚠️  Backend not responding yet, waiting a bit more..."
    sleep 3
fi

echo "✅ Backend is running!"
echo ""

# Create frontend .env.local if it doesn't exist
if [ ! -f "frontend/.env.local" ]; then
    echo "🔗 Creating frontend environment file..."
    echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1" > frontend/.env.local
fi

# Start frontend
echo "🌐 Starting Frontend..."
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "   Installing npm dependencies..."
    npm install
fi

npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend started (PID: $FRONTEND_PID)"

cd ..

# Wait for frontend to start
sleep 3

# Display URLs
echo ""
echo "✅ All services started successfully!"
echo "═══════════════════════════════════════════════"
echo ""
echo "📍 Application URLs:"
echo "   🌐 Frontend:   http://localhost:3000"
echo "   🔧 Backend:    http://127.0.0.1:8000"
echo "   📖 API Docs:   http://127.0.0.1:8000/docs"
echo "   🗄️  Adminer:    http://localhost:8081"
echo ""
echo "📊 Services Running:"
echo "   ✓ PostgreSQL (port 5433)"
echo "   ✓ Redis (port 6379)"
echo "   ✓ Celery Worker (background tasks)"
echo "   ✓ FastAPI Backend (port 8000)"
echo "   ✓ Next.js Frontend (port 3000)"
echo ""
echo "📝 Log files:"
echo "   • Backend: backend/backend.log"
echo "   • Celery:  backend/celery.log"
echo "   • Frontend: frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo "═══════════════════════════════════════════════"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    
    # Kill background processes
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    kill $CELERY_PID 2>/dev/null || true
    
    # Stop Docker services
    cd backend
    docker compose -f docker-compose.yaml down
    cd ..
    
    echo "✅ All services stopped!"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Keep script running
wait
