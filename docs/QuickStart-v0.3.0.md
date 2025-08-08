# Silli Bot Quick Start Guide - v0.3.0

This guide will help you set up and run the Silli Bot application locally or in staging.

## Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Telegram Bot Token (from @BotFather)
- Ollama (for AI functionality)

## Environment Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd silli-bot
```

### 2. Environment Configuration

Copy the appropriate environment template:

**For Local Development:**
```bash
cp env.example .env
```

**For Staging:**
```bash
cp env.staging.example .env
```

### 3. Configure Environment Variables

Edit `.env` with your settings:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional (defaults shown)
PWA_HOST=localhost:5173
REASONER_ENABLED=1
LOG_LEVEL=INFO
```

## Models per Environment

Silli Bot uses different AI models optimized for each environment:

> ⚠️ **IMPORTANT**: Staging environment uses `gpt-oss:20b` only. If resources are insufficient, deployment aborts by design. See `ops/reasoner-node.md` for remote reasoner setup.

### Development Environment
- **Model**: `llama3.2:3b` (2.0 GB)
- **Purpose**: Fast iteration and development
- **Performance**: ~5-10s response time
- **Fallback**: Enabled (`REASONER_ALLOW_FALLBACK=1`)
- **Setup**: `ollama pull llama3.2:3b`

### Staging Environment  
- **Model**: `gpt-oss:20b` (larger, higher quality)
- **Purpose**: Demonstrate production-quality responses
- **Performance**: ~10-20s response time
- **Fallback**: Disabled (`REASONER_ALLOW_FALLBACK=0`)
- **Setup**: Remote reasoner node (see `ops/reasoner-node.md`)
- **Requirements**: 32GB+ RAM, dedicated machine

### Production Environment
- **Model**: `gpt-oss:20b` or `gpt-oss:120b`
- **Purpose**: Best quality responses for end users
- **Performance**: Optimized infrastructure
- **Fallback**: Disabled for consistency
- **Setup**: Managed deployment

### Model Configuration

The model behavior is controlled by these environment variables:

```bash
# Model Selection
REASONER_MODEL_HINT=llama3.2:3b    # Primary model to use
REASONER_ALLOW_FALLBACK=1          # Allow fallback if primary unavailable

# Fallback Behavior
# ALLOW_FALLBACK=1: Use available model if hint unavailable
# ALLOW_FALLBACK=0: Return 503 error if hint unavailable
```

## Installation Methods

### Method 1: Docker Compose (Recommended)

1. **Build and start services:**
```bash
docker-compose up --build
```

2. **Services will be available at:**
- Bot: Running in background
- Reasoner API: http://localhost:5001
- PWA: http://localhost:5173 (if running silli-meter)

### Method 2: Local Development

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start Ollama (separate terminal):**
```bash
ollama serve
ollama pull llama3.2:3b  # For development
```

3. **Start Reasoner (separate terminal):**
```bash
cd reasoner
python app.py
```

4. **Start Bot:**
```bash
python -m bot.main
```

## Verification

### 1. Check Model Availability
```bash
# Check installed models
ollama list

# Test reasoner connection
curl http://localhost:5001/health

# Check available models via reasoner
curl http://localhost:5001/models
```

### 2. Test Bot Functionality
```bash
# Send test message to your bot on Telegram
/about

# Check reasoner model status
/reason_model
```

### 3. Run Smoke Tests
```bash
# Test reasoner directly
python qa/reasoner_smoke.py

# Full staging QA (if staging environment)
bash scripts/qa-staging.sh
```

## Common Issues

### Model Not Available
```
Error: model_unavailable, hint: gpt-oss:20b
```
**Solution**: Pull the required model:
```bash
ollama pull gpt-oss:20b
```

### Fallback Disabled in Staging
If `REASONER_ALLOW_FALLBACK=0` and the hinted model isn't available, the reasoner will return a 503 error instead of falling back to an available model.

### Performance Issues
- **Development**: Use `llama3.2:3b` for faster responses
- **Staging**: Ensure adequate CPU/memory for `gpt-oss:20b`
- **Check resources**: `docker stats` to monitor usage

## Model Management Commands

```bash
# List available models
ollama list

# Pull specific model
ollama pull llama3.2:3b
ollama pull gpt-oss:20b

# Remove unused models
ollama rm <model-name>

# Check model info
ollama show <model-name>
```

## Development Workflow

1. **Local Development**: Use `llama3.2:3b` with fallback enabled
2. **Feature Testing**: Test with staging model configuration
3. **Staging Deployment**: Use `gpt-oss:20b` with strict mode
4. **Production**: Use production-grade models with monitoring

## Support

For issues:
1. Check logs: `docker-compose logs <service-name>`
2. Verify environment variables: `printenv | grep REASONER`
3. Test model availability: `/reason_model` command in bot
4. Run diagnostics: `python qa/reasoner_smoke.py`

---

**Version**: v0.3.0  
**Last Updated**: August 2025
