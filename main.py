#!/usr/bin/env python3
"""
SilliAIBot - Main Application Entry Point
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import Settings
from src.bot.handlers import setup_handlers
from src.database.connection import init_database
from loguru import logger


async def main():
    """Main application entry point."""
    try:
        # Load settings
        settings = Settings()
        
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Setup and start bot
        from telegram.ext import Application
        
        # Create application
        application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Setup handlers
        setup_handlers(application)
        logger.info("Bot handlers configured successfully")
        
        # Start the bot
        logger.info("Starting SilliAIBot...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("SilliAIBot is running! Press Ctrl+C to stop.")
        
        # Keep the bot running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down SilliAIBot...")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            
    except Exception as e:
        logger.error(f"Failed to start SilliAIBot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 