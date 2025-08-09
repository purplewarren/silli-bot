.PHONY: qa-reason help

# QA target for testing reasoner service
qa-reason:
	@echo "🧪 Testing Reasoner Service..."
	@if python3 qa/probe_reasoner.py; then \
		echo "✅ PASS: Reasoner service is working correctly"; \
	else \
		echo "❌ FAIL: Reasoner service test failed"; \
		exit 1; \
	fi

help:
	@echo "Available targets:"
	@echo "  qa-reason    Test the reasoner service (requires gpt-oss:20b)"
	@echo "  help         Show this help message"
