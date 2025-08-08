#!/bin/bash
# Staging Deployment Script
# Deploys and validates staging environment

set -e  # Exit on any error

echo "🚀 Deploying Silli Bot to Staging"
echo "=================================="

# Configuration
REASONER_URL="${REASONER_BASE_URL:-http://localhost:5001}"
EXPECTED_MODEL="${REASONER_MODEL_HINT:-gpt-oss:20b}"

echo "📋 Configuration:"
echo "  • Reasoner URL: $REASONER_URL"
echo "  • Expected Model: $EXPECTED_MODEL"
echo "  • Allow Fallback: false (strict mode)"
echo ""

# Preflight checks
echo "🔍 Preflight Checks"
echo "-------------------"

# Check reasoner health
echo "  • Checking reasoner health..."
if ! curl -s --max-time 10 "$REASONER_URL/health" > /dev/null; then
    echo "❌ Reasoner health check failed"
    echo "   Make sure the remote reasoner node is running and accessible"
    exit 1
fi
echo "✅ Reasoner health check passed"

# Check model availability
echo "  • Checking model availability..."
MODELS_RESPONSE=$(curl -s --max-time 10 "$REASONER_URL/models")
if [ $? -ne 0 ]; then
    echo "❌ Failed to get models from reasoner"
    exit 1
fi

# Validate expected model is available
if echo "$MODELS_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    names = [model.get('name', '') for model in models]
    expected = '$EXPECTED_MODEL'
    if expected in names:
        print('✅ Expected model found')
        sys.exit(0)
    else:
        print(f'❌ Expected model {expected} not found')
        print(f'Available models: {names}')
        sys.exit(1)
except Exception as e:
    print(f'❌ Error parsing models response: {e}')
    sys.exit(1)
"; then
    echo "✅ Model validation passed"
else
    echo "❌ Model validation failed"
    echo "   Make sure gpt-oss:20b is pulled on the remote reasoner node"
    exit 1
fi

echo "✅ All preflight checks passed"
echo ""

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.staging.yml down

# Build and start services
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.staging.yml up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if all containers are running
echo "🔍 Checking container status..."
if ! docker-compose -f docker-compose.staging.yml ps | grep -q "Up"; then
    echo "❌ Not all containers are running"
    docker-compose -f docker-compose.staging.yml ps
    exit 1
fi

echo "✅ All containers are running"

# Note: Preflight checks already validated reasoner and model availability
echo "✅ Reasoner and model validation completed during preflight"

# Run QA tests
echo "🧪 Running QA tests..."
if ./scripts/qa-staging.sh; then
    echo "✅ QA tests passed"
else
    echo "❌ QA tests failed"
    exit 1
fi

echo ""
echo "🎉 Staging deployment successful!"
echo "✅ Environment is ready for pilot testing"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.staging.yml ps
echo ""
echo "🔗 Access Points:"
echo "  • Bot: Running (Telegram)"
echo "  • Reasoner API: http://localhost:5001"
echo "  • Health Check: http://localhost:5001/health"
echo "  • Model Status: http://localhost:5001/status"
echo ""
echo "📝 Next Steps:"
echo "  1. Test bot functionality"
echo "  2. Monitor logs: docker-compose -f docker-compose.staging.yml logs -f"
echo "  3. Begin pilot testing"
echo "  4. Collect user feedback"
