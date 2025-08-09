"""
Configuration management for Silli Bot
Centralizes environment variable parsing and provides typed configuration
"""

import os
from typing import Optional

class Config:
    """Centralized configuration for Silli Bot"""
    
    # Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "replace_me")
    ORG_NAME: str = os.getenv("ORG_NAME", "Silli")
    PWA_HOST: str = os.getenv("PWA_HOST", "localhost:5173")
    KEEP_RAW_MEDIA: bool = os.getenv("KEEP_RAW_MEDIA", "false").lower() in ("true", "1", "yes", "on")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Reasoner Configuration
    REASONER_BASE_URL: str = os.getenv("REASONER_BASE_URL", "http://localhost:5001")
    REASONER_ENABLED: bool = os.getenv("REASONER_ENABLED", "0").lower() in ("1", "true", "yes", "on")
    REASONER_MODEL_HINT: str = os.getenv("REASONER_MODEL_HINT", "llama3.2:3b")
    REASONER_ALLOW_FALLBACK: bool = os.getenv("REASONER_ALLOW_FALLBACK", "1").lower() in ("1", "true", "yes", "on")
    REASONER_TEMP: float = float(os.getenv("REASONER_TEMP", "0.2"))
    REASONER_TIMEOUT: int = int(os.getenv("REASONER_TIMEOUT", "8"))
    
    # AI opt-in default behavior
    REASONER_DEFAULT_ON: bool = os.getenv("REASONER_DEFAULT_ON", "0").lower() in ("1", "true", "yes", "on")
    
    # Proactive Insights
    PROACTIVE_CRON_S: int = int(os.getenv("PROACTIVE_CRON_S", "10800"))  # 3 hours default
    
    # Dyad Configuration
    DYAD_REGISTRY_PATH: str = os.getenv("DYAD_REGISTRY_PATH", "dyads/dyads.yaml")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if cls.TELEGRAM_BOT_TOKEN == "replace_me":
            return False
        return True
    
    @classmethod
    def get_reasoner_config(cls) -> dict:
        """Get reasoner configuration as dict"""
        return {
            "base_url": cls.REASONER_BASE_URL,
            "enabled": cls.REASONER_ENABLED,
            "model_hint": cls.REASONER_MODEL_HINT,
            "allow_fallback": cls.REASONER_ALLOW_FALLBACK,
            "temperature": cls.REASONER_TEMP,
            "timeout": cls.REASONER_TIMEOUT,
            "default_on": cls.REASONER_DEFAULT_ON
        }

# Global config instance
config = Config()
