"""
Utility functions for Silli Bot
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

def convert_pwa_to_bot_format(pwa_data: dict) -> dict:
    """
    Convert PWA session data to bot format.
    
    Args:
        pwa_data: Raw PWA session data
        
    Returns:
        Converted data in bot format
    """
    try:
        # Extract basic fields
        family_id = pwa_data.get("family_id", "")
        session_id = pwa_data.get("session_id", "")
        mode = pwa_data.get("mode", "helper")
        duration_s = pwa_data.get("duration_s", 0)
        
        # Extract score (handle different formats)
        score = pwa_data.get("score", {})
        if isinstance(score, (int, float)):
            score = {"long": score}
        elif isinstance(score, dict):
            # Ensure we have the expected structure
            if "long" not in score and "mid" in score:
                score["long"] = score["mid"]
            elif "long" not in score and "short" in score:
                score["long"] = score["short"]
        
        # Extract badges
        badges = pwa_data.get("badges", [])
        if isinstance(badges, str):
            badges = [badges] if badges else []
        
        # Extract features summary
        features_summary = pwa_data.get("features_summary", {})
        if not isinstance(features_summary, dict):
            features_summary = {}
        
        # Extract additional data
        additional_data = pwa_data.get("additional_data", {})
        if not isinstance(additional_data, dict):
            additional_data = {}
        
        # Build converted data
        converted = {
            "family_id": family_id,
            "session_id": session_id,
            "mode": mode,
            "duration_s": duration_s,
            "score": score,
            "badges": badges,
            "features_summary": features_summary,
            "additional_data": additional_data,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Converted PWA data for session {session_id}")
        return converted
        
    except Exception as e:
        logger.error(f"Error converting PWA data: {e}")
        # Return minimal valid data
        return {
            "family_id": pwa_data.get("family_id", ""),
            "session_id": pwa_data.get("session_id", ""),
            "mode": "helper",
            "duration_s": 0,
            "score": {},
            "badges": [],
            "features_summary": {},
            "additional_data": {},
            "timestamp": datetime.now().isoformat()
        }

def generate_session_token(family_id: str, session_id: str) -> str:
    """
    Generate a session token for PWA access.
    
    Args:
        family_id: Family identifier
        session_id: Session identifier
        
    Returns:
        JWT token string
    """
    try:
        import jwt
        from datetime import timedelta
        
        payload = {
            "family_id": family_id,
            "session_id": session_id,
            "exp": datetime.now() + timedelta(minutes=10)
        }
        
        secret_key = "silli-session-secret-2024"  # In production, use env var
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        return token
        
    except Exception as e:
        logger.error(f"Error generating session token: {e}")
        return ""

def extract_dyad_label(labels: list) -> str:
    """Extract dyad from labels list"""
    for label in labels:
        if label.startswith("dyad:"):
            return label.split(":", 1)[1]
    return "night"  # default
