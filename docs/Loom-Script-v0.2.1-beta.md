# Loom Video Script - Silli Bot v0.2.1-beta Demo
**Duration: 2 minutes**

## Opening (0:00-0:15)
- **Title Card**: "Silli Bot v0.2.1-beta - AI-Powered Parent Helper"
- **Hook**: "Privacy-first AI that runs entirely on your device"
- **Quick Overview**: Show system architecture diagram

## Prerequisites Check (0:15-0:30)
- **Terminal**: Show `python3 --version`, `node --version`, `ollama --version`
- **Highlight**: All required software installed and ready

## Step 1: Ollama Setup (0:30-0:45)
- **Command**: `ollama pull llama3.2:3b`
- **Show**: Download progress (3.2GB model)
- **Command**: `ollama serve`
- **Result**: "✅ Ollama runtime connected"

## Step 2: Reasoner Service (0:45-1:00)
- **Command**: `python reasoner/app.py`
- **Show**: Flask server starting on localhost:5001
- **Highlight**: AI reasoning service ready

## Step 3: Telegram Bot (1:00-1:15)
- **Command**: `python -m bot.main`
- **Show**: Bot starting with reasoner integration
- **Highlight**: "Reasoner enabled: True"

## Step 4: Live Demo (1:15-1:45)
- **Telegram**: Open mobile app
- **Command**: `/start` - Show bot welcome
- **Command**: `/dyads` - Show available helpers
- **Command**: `/reason_status` - Show AI status
- **Highlight**: Real-time AI responses

## Performance Demo (1:45-2:00)
- **QA Test**: Run `python qa/reasoner_smoke.py`
- **Show**: Cache performance (3.2ms vs 1435ms)
- **Highlight**: 99.8% latency improvement

## Closing (2:00-2:15)
- **Summary**: "Complete AI system running locally"
- **Call to Action**: "Check docs/QuickStart-v0.2.1-beta.md"
- **End Card**: "Privacy-first AI for parents"

---

## Key Visual Elements

### Terminal Windows
- **Window 1**: Ollama setup and serving
- **Window 2**: Reasoner service running
- **Window 3**: Bot startup and logs
- **Window 4**: QA testing and performance

### Mobile Screen
- **Telegram App**: Show bot interactions
- **Commands**: `/start`, `/dyads`, `/reason_status`
- **Responses**: AI-generated tips and insights

### Performance Metrics
- **Cache Stats**: Show 80% hit rate
- **Latency**: Demonstrate 3.2ms response time
- **System Health**: All services green

## Technical Notes

### Script Flow
1. **Setup** (45s): Show all prerequisites and services starting
2. **Demo** (45s): Live Telegram interaction with AI
3. **Performance** (30s): QA testing and metrics

### Key Messages
- **Privacy**: Everything runs locally
- **Performance**: 99.8% faster with cache
- **Ease of Use**: Simple 4-step setup
- **AI Power**: Real-time insights for parents

### Troubleshooting Shots
- **If model missing**: Show `ollama pull` command
- **If port conflict**: Show `lsof -i :5001` and kill process
- **If bot not responding**: Show health check `curl localhost:5001/health`

## Production Notes

### Recording Setup
- **Screen Recording**: Terminal windows + mobile screen
- **Audio**: Clear narration of each step
- **Pacing**: 2 minutes total, smooth transitions

### Post-Production
- **Captions**: Add key command highlights
- **Zoom**: Focus on important terminal output
- **Callouts**: Highlight performance metrics

### Distribution
- **GitHub**: Link in README.md
- **Documentation**: Reference in QuickStart guide
- **Marketing**: Showcase AI capabilities
