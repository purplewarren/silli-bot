#!/bin/bash

# Staging Deployment Script
# Usage: ./scripts/deploy-staging.sh

set -e

echo "🚀 Starting Silli Bot Staging Deployment..."

# Check if we're in the right directory
if [ ! -f "docker-compose.staging.yml" ]; then
    echo "❌ Error: docker-compose.staging.yml not found. Run from project root."
    exit 1
fi

# Check environment file
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found. Please copy env.staging.example to .env and update values."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs ssl

# Generate self-signed SSL certificate for staging
if [ ! -f "ssl/staging.silli.ai.crt" ]; then
    echo "🔐 Generating SSL certificate..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/staging.silli.ai.key \
        -out ssl/staging.silli.ai.crt \
        -subj "/C=US/ST=State/L=City/O=Silli/CN=staging.silli.ai"
fi

# Pull latest images
echo "📦 Pulling Docker images..."
docker-compose -f docker-compose.staging.yml pull

# Build bot image
echo "🔨 Building bot image..."
docker-compose -f docker-compose.staging.yml build bot

# Stop existing services
echo "🛑 Stopping existing services..."
docker-compose -f docker-compose.staging.yml down

# Start services
echo "▶️ Starting services..."
docker-compose -f docker-compose.staging.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check
echo "🏥 Running health checks..."
if curl -f http://localhost/health; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker-compose -f docker-compose.staging.yml logs
    exit 1
fi

# Check scheduler status
echo "⏰ Checking scheduler status..."
if curl -f http://localhost/scheduler; then
    echo "✅ Scheduler check passed"
else
    echo "⚠️ Scheduler check failed (may be normal during startup)"
fi

echo "🎉 Staging deployment complete!"
echo "📊 Services:"
echo "   - Bot: http://localhost:8000"
echo "   - Reasoner: http://localhost:5001"
echo "   - Nginx: http://localhost"
echo "   - Health: http://localhost/health"

echo "📝 Next steps:"
echo "   1. Run QA tests: python qa/reasoner_smoke.py --cache-hit"
echo "   2. Test onboarding flow manually"
echo "   3. Monitor logs: docker-compose -f docker-compose.staging.yml logs -f"
