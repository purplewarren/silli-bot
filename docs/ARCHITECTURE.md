# Silli Bot & PWA Architecture

## Overview

Silli Bot provides a privacy-first parent helper that analyzes audio sessions through a Progressive Web App (PWA) and automatically ingests results via a secure relay system.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │  Cloudflare      │    │   PWA           │
│   (aiogram)     │    │  Worker + KV     │    │   (Vite/TS)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         │  Background Pull      │  Store Session       │  Send Session
         │  (every 15s)         │  (JWT validated)     │  (JWT auth)
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 │  KV Storage
                                 │  - session:<chat_id>:<session_id>
                                 │  - pending:<chat_id> (list)
```

## Data Flow

### 1. Session Initiation
```
User → Bot: /summon_helper
Bot → User: PWA link with JWT token
```

### 2. PWA Session Recording
```
PWA → Audio Analysis → Session JSON → Worker /ingest
```

### 3. Secure Storage
```
Worker → Validate JWT → Store in KV → Return success
```

### 4. Automatic Ingestion
```
Bot → Background loop → Worker /pull → Process sessions → Store events
```

## Security Model

### JWT Token Flow
1. **Bot generates JWT** with claims: `{chat_id, family_id, session_id, exp}`
2. **PWA receives JWT** via URL parameter `tok=...`
3. **PWA strips JWT** from URL history immediately
4. **Worker validates JWT** using shared `RELAY_SECRET`
5. **Bot authenticates** to Worker using `X-Auth: RELAY_SECRET`

### Privacy Features
- ✅ **No bot token in browser**: JWT tokens only
- ✅ **Short-lived tokens**: 30-minute expiration
- ✅ **Derived metrics only**: No audio/video stored
- ✅ **Server-side validation**: All requests validated
- ✅ **Encrypted communication**: HTTPS throughout

## Components

### 1. Telegram Bot (`bot/`)
- **Framework**: aiogram
- **Features**: Command handling, background pull loop
- **Storage**: JSONL event logs
- **Security**: Environment-based configuration

### 2. Cloudflare Worker (`relay/`)
- **Runtime**: Cloudflare Workers
- **Storage**: KV namespace (`SILLI_SESSIONS`)
- **Endpoints**: `/ingest` (POST), `/pull` (GET)
- **Security**: JWT validation, X-Auth authentication

### 3. Progressive Web App (`silli-meter/`)
- **Framework**: Vite + TypeScript
- **Features**: Real-time audio analysis, session export
- **Hosting**: GitHub Pages
- **Security**: JWT tokens, no bot token exposure

## Deployment

### Environment Variables
```bash
# Bot (.env)
TELEGRAM_BOT_TOKEN=***
RELAY_SECRET=***            # same as Worker
RELAY_PULL_URL=https://silli-auto-ingest-relay.silli-tg-bot.workers.dev/pull
RELAY_PULL_INTERVAL_S=15
TEST_CHAT_ID=2130406580     # MVP only

# Worker (wrangler secrets)
RELAY_SECRET=***
BOT_TOKEN=***               # for optional Telegram notifications
```

### Infrastructure
- **Bot**: Python server (any hosting)
- **Worker**: Cloudflare Workers (free tier)
- **PWA**: GitHub Pages (free)
- **Storage**: Cloudflare KV (free tier)

## Error Handling

### PWA Fallbacks
1. **Network failure**: Download session files locally
2. **Token expired**: Prompt user to re-summon
3. **Offline mode**: Queue sessions for later

### Bot Resilience
1. **Pull failures**: Log errors, continue polling
2. **Duplicate sessions**: Idempotent processing
3. **Invalid data**: Skip malformed sessions

### Worker Reliability
1. **KV limits**: 7-day TTL on sessions
2. **Rate limiting**: 100,000 requests/day (free)
3. **Error responses**: Proper HTTP status codes

## Monitoring

### Logs
- **Bot**: `logs/silli_bot.log` (rotated daily)
- **Worker**: Cloudflare dashboard
- **PWA**: Browser console

### Metrics
- **Sessions/day**: Count ingest_session_report events
- **Success rate**: Monitor pull loop errors
- **Storage usage**: KV namespace utilization

## Future Enhancements

### P0 (This Week)
- Dynamic roster (replace TEST_CHAT_ID)
- Offline queue in PWA
- Replay guard implementation

### P1 (Next Sprint)
- KV prefix listing optimization
- Pull loop backoff/jitter
- Error telemetry dashboard

### P2 (Future)
- Metrics dashboard
- Internationalization
- Advanced analytics 