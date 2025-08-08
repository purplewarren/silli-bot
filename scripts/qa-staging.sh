#!/bin/bash
# QA Staging Script
# Validates staging deployment with model validation

set -e  # Exit on any error

echo "🚀 Starting Staging QA Validation"
echo "=================================="

# Configuration
REASONER_URL="http://localhost:5001"
EXPECTED_MODEL="${REASONER_MODEL_HINT:-llama3.2:1b}"

echo "📋 Configuration:"
echo "  • Reasoner URL: $REASONER_URL"
echo "  • Expected Model: $EXPECTED_MODEL"
echo ""

# Preflight check: Verify model availability
echo "🔍 Preflight Check: Model Availability"
echo "--------------------------------------"

# Check if reasoner is responding
if ! curl -s --max-time 5 "$REASONER_URL/health" > /dev/null; then
    echo "❌ Reasoner health check failed"
    exit 1
fi

# Check if expected model is available
MODELS_RESPONSE=$(curl -s --max-time 10 "$REASONER_URL/models")
if [ $? -ne 0 ]; then
    echo "❌ Failed to get models from reasoner"
    exit 1
fi

# Extract model names from JSON response
MODEL_NAMES=$(echo "$MODELS_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    names = [model.get('name', '') for model in models]
    print(' '.join(names))
except:
    print('')
")

if [ -z "$MODEL_NAMES" ]; then
    echo "❌ No models found in reasoner response"
    echo "Response: $MODELS_RESPONSE"
    exit 1
fi

echo "📋 Available models: $MODEL_NAMES"

# Check if expected model is in the list
if echo "$MODEL_NAMES" | grep -q "$EXPECTED_MODEL"; then
    echo "✅ Expected model '$EXPECTED_MODEL' is available"
else
    echo "❌ Expected model '$EXPECTED_MODEL' is NOT available"
    echo "Available models: $MODEL_NAMES"
    exit 1
fi

echo ""

# Run smoke tests with strict model validation
echo "🧪 Running Smoke Tests (Strict Mode)"
echo "------------------------------------"

# Set environment for strict testing
export REASONER_ALLOW_FALLBACK=0

# Run smoke test with expected model
if python3 qa/reasoner_smoke.py --expect-model gpt-oss:20b; then
    echo "✅ Smoke tests passed"
else
    echo "❌ Smoke tests failed"
    exit 1
fi

echo ""

# Test reasoner status endpoint
echo "📊 Testing Reasoner Status Endpoint"
echo "-----------------------------------"

STATUS_RESPONSE=$(curl -s --max-time 10 "$REASONER_URL/status")
if [ $? -ne 0 ]; then
    echo "❌ Failed to get reasoner status"
    exit 1
fi

# Validate status response
echo "$STATUS_RESPONSE" | python3 -c "
import json, sys, os
try:
    data = json.load(sys.stdin)
    expected_model = os.environ.get('REASONER_MODEL_HINT', 'llama3.2:1b')
    
    # Check required fields
    required_fields = ['enabled', 'model_hint', 'allow_fallback', 'last_model_used', 'cache_hit_rate']
    for field in required_fields:
        if field not in data:
            print(f'❌ Missing required field: {field}')
            sys.exit(1)
    
    # Validate model hint
    if data['model_hint'] != expected_model:
        print(f'❌ Model hint mismatch: expected {expected_model}, got {data[\"model_hint\"]}')
        sys.exit(1)
    
    # Validate fallback setting
    if data['allow_fallback'] != False:
        print(f'❌ Fallback should be disabled in staging, got {data[\"allow_fallback\"]}')
        sys.exit(1)
    
    print('✅ Status endpoint validation passed')
    print(f'  • Model hint: {data[\"model_hint\"]}')
    print(f'  • Allow fallback: {data[\"allow_fallback\"]}')
    print(f'  • Cache hit rate: {data[\"cache_hit_rate\"]}')
    
except Exception as e:
    print(f'❌ Status validation failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "🎉 All QA checks passed!"
echo "✅ Staging deployment is ready for pilot testing"
