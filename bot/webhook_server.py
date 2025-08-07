"""
Webhook server for direct PWA communication
"""

import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from loguru import logger
from .models import EventRecord
from .storage import Storage
from .handlers import convert_pwa_to_bot_format, validate_session_token

app = FastAPI()
storage = Storage()

# Store communication tokens (same as in handlers.py)
SESSION_TOKENS = {}

@app.post("/webhook/pwa-session")
async def handle_pwa_session(request: Request):
    """Handle PWA session submission via webhook."""
    try:
        data = await request.json()
        
        # Extract data
        comm_token = data.get('comm_token')
        family_id = data.get('family_id')
        session_data = data.get('session_data', {})
        
        if not comm_token or not family_id:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Validate communication token
        session_validation = validate_session_token(comm_token, family_id)
        if not session_validation:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Clean up used token
        del SESSION_TOKENS[comm_token]
        
        # Convert PWA format to bot format
        converted_data = convert_pwa_to_bot_format(session_data)
        
        # Create event record
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=converted_data['session_id'],
            phase=converted_data['mode'],
            actor="parent",
            event="ingest_session_report",
            labels=converted_data.get('badges', []),
            features=converted_data.get('features_summary'),
            score=converted_data.get('score'),
            suggestion_id=None
        )
        
        # Store the event
        storage.append_event(event)
        
        # Send confirmation to Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = family_id.replace('fam_', '')
        
        confirmation = (
            f"✅ **PWA Session Received!**\n\n"
            f"📊 **Score:** {converted_data.get('score', 'N/A')}/100\n"
            f"⏱️ **Duration:** {converted_data.get('duration_s', 0)}s\n"
            f"🏷️ **Badges:** {', '.join(converted_data.get('badges', [])) if converted_data.get('badges') else 'None'}\n"
            f"📅 **Session:** {converted_data['session_id']}\n\n"
            f"Session data has been automatically added to your profile.\n"
            f"Use `/list` to see all your sessions."
        )
        
        # Send to Telegram
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": confirmation,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send Telegram message: {response.text}")
                raise HTTPException(status_code=500, detail="Failed to send confirmation")
        
        return JSONResponse({
            "status": "success", 
            "message": "Session processed successfully",
            "session_id": converted_data['session_id']
        })
        
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 