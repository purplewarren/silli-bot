"""
Internationalization (i18n) support for Silli Bot
Manages user language preferences and locale persistence
"""

import os
from typing import Optional
from loguru import logger
from .profiles import profiles

# Supported languages
SUPPORTED_LOCALES = ["en", "pt_br"]
DEFAULT_LOCALE = "en"

def get_locale(chat_id: int) -> str:
    """
    Get the locale for a chat ID.
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        Locale string (e.g., "en", "pt_br")
    """
    try:
        # Get profile for this chat
        profile = profiles.get_profile_by_chat_sync(chat_id)
        if profile and "locale" in profile:
            locale = profile["locale"]
            if locale in SUPPORTED_LOCALES:
                return locale
            else:
                logger.warning(f"Invalid locale '{locale}' for chat {chat_id}, falling back to {DEFAULT_LOCALE}")
                return DEFAULT_LOCALE
        
        # Fallback to default
        return DEFAULT_LOCALE
        
    except Exception as e:
        logger.error(f"Error getting locale for chat {chat_id}: {e}")
        return DEFAULT_LOCALE

def set_locale(chat_id: int, locale: str) -> bool:
    """
    Set the locale for a chat ID.
    
    Args:
        chat_id: Telegram chat ID
        locale: Locale string (e.g., "en", "pt_br")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate locale
        if locale not in SUPPORTED_LOCALES:
            logger.error(f"Unsupported locale: {locale}")
            return False
        
        # Update profile with new locale
        success = profiles.upsert_fields_sync(chat_id, {"locale": locale})
        
        if success:
            logger.info(f"Set locale to '{locale}' for chat {chat_id}")
        else:
            logger.error(f"Failed to set locale '{locale}' for chat {chat_id}")
            
        return success
        
    except Exception as e:
        logger.error(f"Error setting locale for chat {chat_id}: {e}")
        return False

def get_supported_locales() -> list:
    """Get list of supported locales."""
    return SUPPORTED_LOCALES.copy()

def is_supported_locale(locale: str) -> bool:
    """Check if a locale is supported."""
    return locale in SUPPORTED_LOCALES
