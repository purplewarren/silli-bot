"""
Webhook handler for direct PWA communication
"""

import os
import json
from datetime import datetime
from loguru import logger
from .models import EventRecord
from .storage import Storage
from .handlers import convert_pwa_to_bot_format, validate_session_token, SESSION_TOKENS

storage = Storage()

async def handle_pwa_webhook(data: dict, bot) -> dict:
    """Handle PWA session submission via webhook."""
    try:
        # Extract data
        comm_token = data.get('comm_token')
        family_id = data.get('family_id')
        session_data = data.get('session_data', {})
        
        if not comm_token or not family_id:
            return {"error": "Missing required fields"}
        
        # Validate communication token
        session_validation = validate_session_token(comm_token, family_id)
        if not session_validation:
            return {"error": "Invalid or expired token"}
        
        # Clean up used token
        if comm_token in SESSION_TOKENS:
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
        await bot.send_message(
            chat_id=chat_id,
            text=confirmation,
            parse_mode="Markdown"
        )
        
        logger.info(f"PWA session processed via webhook: {converted_data['session_id']}")
        
        return {
            "status": "success", 
            "message": "Session processed successfully",
            "session_id": converted_data['session_id']
        }
        
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}")
        return {"error": "Internal server error"} 