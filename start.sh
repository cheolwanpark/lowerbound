#!/bin/bash

# Quick start script for crypto-portfolio service

set -e

echo "=========================================="
echo "Crypto Portfolio OHLCV Service"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env created"
    echo ""
    echo "⚠️  Please edit .env and set your configuration (especially API_KEY)"
    echo ""
fi

# Start services
echo "Starting services with Docker Compose..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 5

# Check health
echo ""
echo "Checking service health..."
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "API not ready yet"

echo ""
echo "=========================================="
echo "Services Started!"
echo "=========================================="
echo ""
echo "📊 API Documentation:  http://localhost:8000/docs"
echo "❤️  Health Check:      http://localhost:8000/api/v1/health"
echo "📈 Assets Coverage:    http://localhost:8000/api/v1/assets"
echo ""
echo "View logs:"
echo "  docker-compose logs -f api"
echo "  docker-compose logs -f scheduler"
echo ""
echo "Stop services:"
echo "  docker-compose down"
echo ""
