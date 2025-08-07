"""
Webhook endpoint for secure PWA communication
"""

import os
import json
import hashlib
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
from loguru import logger

app = FastAPI()

# Store communication tokens (same as in handlers.py)
SESSION_TOKENS = {}

def validate_comm_token(token: str, family_id: str) -> dict:
    """Validate a communication token."""
    if token not in SESSION_TOKENS:
        return None
    
    session_data = SESSION_TOKENS[token]
    
    # Check if token is expired (24 hours)
    if (datetime.now() - session_data['created_at']).total_seconds() > 86400:
        del SESSION_TOKENS[token]
        return None
    
    # Check if family_id matches
    if session_data['family_id'] != family_id:
        return None
    
    return session_data

@app.post("/webhook/pwa-session")
async def handle_pwa_session(request: Request):
    """Handle PWA session submission via webhook."""
    try:
        data = await request.json()
        
        # Extract data
        comm_token = data.get('comm_token')
        family_id = data.get('family_id')
        session_id = data.get('session_id')
        score = data.get('score', 0)
        duration = data.get('duration', '0:00')
        badges = data.get('badges', [])
        
        if not comm_token or not family_id:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Validate communication token
        session_data = validate_comm_token(comm_token, family_id)
        if not session_data:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Clean up used token
        del SESSION_TOKENS[comm_token]
        
        # Send message to Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = family_id.replace('fam_', '')
        
        message = (
            f"📊 **PWA Session Complete!**\n\n"
            f"📊 Score: {score}/100\n"
            f"⏱️ Duration: {duration}\n"
            f"🏷️ Badges: {', '.join(badges) if badges else 'None detected'}\n"
            f"📅 Session: {session_id}\n"
            f"🔐 Comm Token: {comm_token}\n\n"
            f"Session data has been sent to the bot."
        )
        
        # Send to Telegram
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to send Telegram message: {response.text}")
                raise HTTPException(status_code=500, detail="Failed to send message")
        
        return JSONResponse({"status": "success", "message": "Session processed successfully"})
        
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 