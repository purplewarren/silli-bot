#!/bin/bash

# Staging QA Test Script
# Usage: ./scripts/qa-staging.sh

set -e

echo "🧪 Starting Silli Bot Staging QA Tests..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "\n${YELLOW}Running: $test_name${NC}"
    echo "Command: $test_command"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASS: $test_name${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL: $test_name${NC}"
        ((TESTS_FAILED++))
    fi
}

# Check if services are running
echo "🔍 Checking service status..."

# Health check
run_test "Health Check" "curl -f http://localhost/health"

# Bot service check
run_test "Bot Service" "docker ps | grep silli-bot-staging"

# Reasoner service check
run_test "Reasoner Service" "docker ps | grep silli-reasoner-staging"

# Nginx service check
run_test "Nginx Service" "docker ps | grep silli-nginx-staging"

# Ollama models check
echo -e "\n${YELLOW}Checking Ollama models...${NC}"
if docker exec silli-reasoner-staging ollama list | grep -q "gpt-oss-20b\|llama3.2:3b"; then
    echo -e "${GREEN}✅ Ollama models found${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Ollama models not found${NC}"
    echo "Pulling models..."
    docker exec silli-reasoner-staging ollama pull gpt-oss-20b
    docker exec silli-reasoner-staging ollama pull llama3.2:3b
    ((TESTS_PASSED++))
fi

# Python tests
echo -e "\n${YELLOW}Running Python tests...${NC}"
run_test "Unit Tests" "python -m pytest tests/ -v --tb=short"

# Reasoner smoke test
echo -e "\n${YELLOW}Running reasoner smoke test...${NC}"
run_test "Reasoner Smoke Test" "python qa/reasoner_smoke.py --cache-hit"

# Manual test checklist
echo -e "\n${YELLOW}Manual Test Checklist:${NC}"
echo "Please complete these tests manually:"
echo "1. New user onboarding flow:"
echo "   - Start bot with /start"
echo "   - Complete greeting card → Learn More → Road-show"
echo "   - Create family profile (9 steps)"
echo "   - Enable Dyads with consent"
echo "   - Verify /help shows new commands"
echo ""
echo "2. Language switching:"
echo "   - Use /lang pt_br"
echo "   - Verify all text in Portuguese"
echo "   - Switch back with /lang en"
echo ""
echo "3. Dyad functionality:"
echo "   - Use /summondyad"
echo "   - Launch Night Helper PWA"
echo "   - Complete session and export JSON"
echo "   - Verify data ingestion"
echo ""
echo "4. Proactive features:"
echo "   - Check /scheduler status"
echo "   - Test /reasoning toggle"
echo "   - Verify /insights command"
echo ""

# Summary
echo -e "\n${YELLOW}QA Test Summary:${NC}"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All automated tests passed!${NC}"
    echo "Proceed with manual testing checklist above."
else
    echo -e "${RED}⚠️ Some tests failed. Please investigate before proceeding.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Complete manual test checklist"
echo "2. Monitor logs: docker-compose -f docker-compose.staging.yml logs -f"
echo "3. Collect pilot user feedback"
echo "4. Prepare GO/NO-GO decision"
