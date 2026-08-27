#!/bin/bash

# Search Console Agent - Backend Startup Script
# This script starts the database and backend API with a single command

set -e  # Exit on any error

echo "🚀 Starting Search Console Agent Backend..."
echo ""

# Check if .env exists
if [ ! -f "../.env" ]; then
    echo "❌ Error: .env file not found in project root"
    echo "   Please create .env file with required variables"
    exit 1
fi

# Create symlink to .env if it doesn't exist
if [ ! -L ".env" ]; then
    echo "🔗 Creating .env symlink..."
    ln -sfn ../.env .env
fi

# Start PostgreSQL database
echo "🗄️  Starting PostgreSQL database..."
docker compose -f db/docker-compose.yaml up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 3

# Check if database is healthy
if ! docker ps | grep -q "postgres.*healthy"; then
    echo "⚠️  Database not healthy yet, waiting a bit more..."
    sleep 5
fi

echo "✅ Database is running!"
echo ""

# Check if migrations are up to date
echo "🔄 Checking database migrations..."
uv run alembic current 2>/dev/null || {
    echo "⚠️  No migrations applied yet"
    echo "📝 Running migrations..."
    uv run alembic upgrade head
}

echo "✅ Database migrations up to date!"
echo ""

# Start the backend API
echo "🔧 Starting FastAPI backend..."
echo "   API: http://127.0.0.1:8000"
echo "   Docs: http://127.0.0.1:8000/docs"
echo "   Adminer: http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop the server"
echo "═══════════════════════════════════════"

uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
