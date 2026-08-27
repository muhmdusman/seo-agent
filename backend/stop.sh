#!/bin/bash

# Search Console Agent - Backend Stop Script
# This script stops the database gracefully

echo "🛑 Stopping Search Console Agent Backend..."
echo ""

# Stop PostgreSQL database
echo "🗄️  Stopping PostgreSQL database..."
docker compose -f db/docker-compose.yaml down

echo ""
echo "✅ All services stopped!"
echo ""
echo "Note: The backend API stops when you press Ctrl+C"
