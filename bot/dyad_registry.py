"""
Dyad Registry Manager
Handles Dyad metadata, token generation, and session management
"""

import yaml
import jwt
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
from loguru import logger
from .storage import Storage, EventRecord

class DyadRegistry:
    """Manages Dyad metadata and session tokens."""
    
    def __init__(self, registry_path: str = "dyads/dyads.yaml"):
        self.registry_path = Path(registry_path)
        self.storage = Storage()
        self.secret_key = "silli-dyad-secret-key-2024"  # In production, use env var
        
        # Load registry
        self._load_registry()
    
    def _load_registry(self):
        """Load Dyad registry from YAML file."""
        try:
            if not self.registry_path.exists():
                logger.error(f"Dyad registry not found: {self.registry_path}")
                self.registry = {"dyads": {}, "settings": {}}
                return
            
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                self.registry = yaml.safe_load(f)
            
            logger.info(f"Loaded {len(self.registry.get('dyads', {}))} Dyads from registry")
            
        except Exception as e:
            logger.error(f"Failed to load Dyad registry: {e}")
            self.registry = {"dyads": {}, "settings": {}}
    
    def get_dyad(self, dyad_id: str) -> Optional[Dict[str, Any]]:
        """Get Dyad metadata by ID."""
        return self.registry.get("dyads", {}).get(dyad_id)
    
    def get_all_dyads(self) -> Dict[str, Dict[str, Any]]:
        """Get all available Dyads."""
        return self.registry.get("dyads", {})
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get global setting."""
        return self.registry.get("settings", {}).get(key, default)
    
    def generate_session_token(self, family_id: str, dyad_id: str, language: str = "en") -> str:
        """Generate a secure session token for Dyad access."""
        try:
            # Create session metadata
            session_id = f"{family_id}_{dyad_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Token payload
            payload = {
                "family_id": family_id,
                "dyad_id": dyad_id,
                "session_id": session_id,
                "language": language,
                "created_at": datetime.now().isoformat(),
                "exp": datetime.now() + timedelta(minutes=self.get_setting("token_expiry_minutes", 10))
            }
            
            # Generate JWT token
            token = jwt.encode(payload, self.secret_key, algorithm="HS256")
            
            # Log session creation
            event = EventRecord(
                ts=datetime.now(),
                family_id=family_id,
                session_id=session_id,
                phase="dyad_session",
                actor="parent",
                event="dyad_session_created",
                labels=[dyad_id, "session_created"]
            )
            self.storage.append_event(event)
            
            logger.info(f"Generated session token for {dyad_id} - {family_id}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate session token: {e}")
            raise
    
    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode session token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Session token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid session token: {e}")
            return None
    
    def get_dyad_text(self, dyad_id: str, text_key: str, language: str = "en") -> str:
        """Get localized text for a Dyad."""
        dyad = self.get_dyad(dyad_id)
        if not dyad:
            return f"Unknown Dyad: {dyad_id}"
        
        text_data = dyad.get(text_key, {})
        if isinstance(text_data, dict):
            return text_data.get(language, text_data.get("en", f"Missing text: {text_key}"))
        
        return str(text_data)
    
    def get_dyad_consent_text(self, dyad_id: str, language: str = "en") -> str:
        """Get consent text for a Dyad."""
        dyad = self.get_dyad(dyad_id)
        if not dyad:
            return f"Unknown Dyad: {dyad_id}"
        
        consent_data = dyad.get("consent_text", {})
        if isinstance(consent_data, dict):
            return consent_data.get(language, consent_data.get("en", "Consent text not available"))
        
        return str(consent_data)
    
    def create_dyad_url(self, family_id: str, dyad_id: str, language: str = "en") -> str:
        """Create PWA URL for Dyad session."""
        try:
            token = self.generate_session_token(family_id, dyad_id, language)
            pwa_host = "purplewarren.github.io"  # Should come from config
            
            return f"https://{pwa_host}/silli-meter?mode=helper&family={family_id}&dyad={dyad_id}&tok={token}"
            
        except Exception as e:
            logger.error(f"Failed to create Dyad URL: {e}")
            raise
    
    def log_dyad_launch(self, family_id: str, dyad_id: str, session_id: str):
        """Log Dyad launch event."""
        try:
            event = EventRecord(
                ts=datetime.now(),
                family_id=family_id,
                session_id=session_id,
                phase="dyad_launch",
                actor="parent",
                event="dyad_launched",
                labels=[dyad_id, "launched"]
            )
            self.storage.append_event(event)
            
            logger.info(f"Dyad launched: {dyad_id} for {family_id}")
            
        except Exception as e:
            logger.error(f"Failed to log Dyad launch: {e}")
    
    def format_reflection(self, dyad_id: str, session_data: Dict[str, Any], language: str = "en") -> str:
        """Format Dyad-specific reflection message."""
        try:
            dyad = self.get_dyad(dyad_id)
            if not dyad:
                return "Session complete."
            
            template = self.get_dyad_text(dyad_id, "reflection_template", language)
            
            # Format template with session data
            formatted = template.format(**session_data)
            
            return formatted
            
        except Exception as e:
            logger.error(f"Failed to format reflection: {e}")
            return "Session complete."

# Global registry instance
dyad_registry = DyadRegistry()
