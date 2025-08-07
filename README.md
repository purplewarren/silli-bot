# Silli Bot

A privacy-first Telegram bot orchestrator for the Silli AI parent helper MVP.

## Overview

Silli Bot is a Telegram bot that serves as a "Wizard-of-Oz Orchestrator" for the Silli AI parent helper system. It provides two main functions:

1. **PWA Deep Link Generation** - Creates session links for the Parent Night Helper PWA
2. **Voice Analysis** - Analyzes voice notes to provide Wind-Down scores and guidance

## Privacy Guarantees

- **Raw media discarded by default** - Only derived metrics are logged
- **Local processing** - Analysis runs on your machine, no cloud uploads
- **Append-only logs** - Events are logged to `data/events.jsonl` with derived fields only
- **Optional retention** - Set `KEEP_RAW_MEDIA=true` for temporary debugging (24h max)

## Setup

### Prerequisites

1. **Install ffmpeg** (required for audio processing):
   ```bash
   brew install ffmpeg  # macOS
   ```

2. **Create virtual environment and install dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your Telegram bot token
   ```

### Running the Bot

```bash
python -m bot.main
```

## Commands

- `/start` - Consent and assign anonymous family_id
- `/help` - List available commands
- `/summon_helper` - Generate PWA deep link for a session
- `/analyze` - Instructions to send a voice note for analysis
- `/privacy_offline` - Acknowledge bot will not send proactive messages
- `/export` - Download your derived event log

## Voice Analysis

When you send a voice note:

1. **Download** → **ffmpeg** → **16k mono WAV** → **extract features** → **compute Wind-Down Score**
2. **Reply** with text summary and PNG card
3. **Log** derived metrics to `data/events.jsonl`
4. **Delete** raw audio file (unless `KEEP_RAW_MEDIA=true`)

## Data Contracts

### Event JSON Lines (`data/events.jsonl`)

```json
{
  "ts": "2025-08-01T13:22:15.201-03:00",
  "family_id": "fam_001",
  "session_id": "fam_001_2025-08-01_1690900000",
  "phase": "adhoc",
  "actor": "parent|bot|system",
  "event": "voice_analyzed|photo_analyzed|video_analyzed|summon_helper|privacy_offline|consent",
  "labels": ["Speech present","Fluctuating"],
  "features": {
    "level_dbfs": -24.1,
    "centroid_norm": 0.36,
    "rolloff_norm": 0.41,
    "flux_norm": 0.18,
    "vad_fraction": 0.27,
    "stationarity": 0.71
  },
  "score": 68,
  "suggestion_id": "wind_down_v1",
  "pii": false,
  "version": "bot_0.1"
}
```

### Sessions CSV (`data/sessions.csv`)

```
family_id,session_id,date,phase,start_ts,end_ts,time_to_calm_min,adoption_rate,helpfulness_1to7,privacy_1to7,notes
```

## Project Structure

```
silli-bot/
├── bot/
│   ├── __init__.py
│   ├── main.py                 # entrypoint: handlers + polling
│   ├── handlers.py             # command & media handlers
│   ├── analysis_audio.py       # ffmpeg -> WAV -> features -> score/badges/tips
│   ├── analysis_image.py       # (stub) luminance/CCT
│   ├── analysis_video.py       # (stub) motion energy
│   ├── scoring.py              # weights + rules + tips table
│   ├── storage.py              # JSONL append + CSV roll-up + paths
│   ├── cards.py                # PNG summary card renderer (Pillow)
│   └── models.py               # Pydantic schemas for Event, FeatureSummary
├── data/                       # events.jsonl (append-only), sessions.csv
├── logs/
├── env.example
├── requirements.txt
├── .gitignore
└── README.md
```

## Development

### Testing

Run the smoke test:
```bash
python scripts/smoke.py
```

### Privacy Mode

By default, raw media files are deleted after processing. To keep them for debugging:

1. Set `KEEP_RAW_MEDIA=true` in `.env`
2. Files will be retained for 24 hours maximum
3. Check logs for retention warnings

## License

[Add your license here] 