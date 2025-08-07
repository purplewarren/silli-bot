# Changelog

All notable changes to this project will be documented in this file.

## [v0.2.1-beta] - 2025-08-07

### Added
- Complete reasoner integration with Ollama backend
- AI-powered insights for tantrum, meal, and night dyads
- Cache system for improved performance (99.8% latency improvement)
- Comprehensive QA testing framework
- Webhook endpoints for PWA integration
- Telegram bot with full dyad support

### Changed
- Migrated from simple bot to full AI reasoning system
- Enhanced data storage with JSONL format
- Improved tip generation with structured output

### Technical
- Freeze before SQLite migration; JSONL storage retained for one more sprint.
- Reasoner service running on localhost:5001
- Cache hit rate: 80% with 3.2ms average latency
- Model: llama3.2:3b for local AI processing

### Performance
- Initial latency: 1435ms (uncached)
- Cached latency: 3.2ms (99.8% improvement)
- Cache configuration: 256 entries max, 5-minute TTL
- Zero cache evictions, optimal memory usage
