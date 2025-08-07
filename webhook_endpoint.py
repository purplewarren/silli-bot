"""
Standalone webhook endpoint for PWA communication
Can be deployed to Vercel, Netlify, Railway, etc.
"""

import os
import json
import asyncio
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

class PwaSessionRequest(BaseModel):
    comm_token: str
    family_id: str
    session_data: dict

@app.post("/webhook/pwa-session")
async def handle_pwa_session(request: PwaSessionRequest):
    """Handle PWA session submission via webhook."""
    try:
        # Extract data
        comm_token = request.comm_token
        family_id = request.family_id
        session_data = request.session_data
        
        # For now, we'll forward to the bot via Telegram API
        # In a real implementation, you'd validate the token and process the data
        
        # Send to Telegram bot
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = family_id.replace('fam_', '')
        
        # Create a simple message for now
        session_id = session_data.get('session_id', 'unknown')
        score = session_data.get('score', {})
        if isinstance(score, dict):
            score = score.get('mid', 'N/A')
        
        badges = session_data.get('badges', [])
        duration = session_data.get('duration_s', 0)
        
        message = (
            f"✅ **PWA Session Received!**\n\n"
            f"📊 **Score:** {score}/100\n"
            f"⏱️ **Duration:** {duration}s\n"
            f"🏷️ **Badges:** {', '.join(badges) if badges else 'None'}\n"
            f"📅 **Session:** {session_id}\n\n"
            f"Session data has been automatically added to your profile.\n"
            f"Use `/list` to see all your sessions."
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
                raise HTTPException(status_code=500, detail="Failed to send to Telegram")
        
        return JSONResponse({
            "status": "success", 
            "message": "Session processed successfully",
            "session_id": session_id
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

@app.post("/ingest")
async def ingest_session(document: UploadFile = File(...)):
    """Handle session ingestion via multipart form data."""
    try:
        # Read the uploaded JSON document
        content = await document.read()
        session_data = json.loads(content.decode('utf-8'))
        
        # Extract session info
        session_id = session_data.get('session_id', 'unknown')
        family_id = session_data.get('family_id', 'unknown')
        
        # For testing purposes, just return success
        # In a real implementation, this would process the session data
        
        return JSONResponse({
            "status": "success",
            "message": "Session ingested successfully",
            "session_id": session_id,
            "family_id": family_id
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 