"""
Main entry point for Silli Bot
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first, before any other imports
load_dotenv()
from aiogram import Bot, Dispatcher
from loguru import logger
from .handlers import router
from .puller import start_pull_loop
from aiogram import types
from .middlewares import ProfileGateMiddleware
from bot.profiles import profiles
from .handlers_profile import router_profile
from .handlers_insights import router_insights
from .reason_client import create_reasoner_config


def setup_logging():
    """Setup logging configuration."""
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    # Add file handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "silli_bot.log",
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=os.getenv("LOG_LEVEL", "INFO")
    )


def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import ffmpeg
        logger.info("ffmpeg-python available")
    except ImportError:
        logger.error("ffmpeg-python not found. Please install: pip install ffmpeg-python")
        return False
    
    # Check if ffmpeg is installed on system
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        logger.info("ffmpeg system command available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("ffmpeg not found on system. Please install: brew install ffmpeg (macOS)")
        return False
    
    return True


async def set_commands(bot):
    commands = [
        types.BotCommand(command="start", description="Begin and consent to the privacy notice"),
        types.BotCommand(command="help", description="See all available commands"),
        types.BotCommand(command="onboard", description="Set up your Family Profile"),
        types.BotCommand(command="summon_helper", description="Open the Parent Night Helper (PWA)"),
        types.BotCommand(command="analyze", description="Send a voice note for Wind-Down analysis"),
        types.BotCommand(command="insights", description="View AI-aided insights from your sessions"),
        types.BotCommand(command="dyads", description="Show all helpers (Dyads)"),
        types.BotCommand(command="privacy_offline", description="Stop proactive messages (reply-only mode)"),
        types.BotCommand(command="export", description="Download your derived event log (JSONL)"),
        types.BotCommand(command="ingest", description="Upload a PWA session JSON report"),
        types.BotCommand(command="reason_on", description="Enable AI-powered insights for your family"),
        types.BotCommand(command="reason_off", description="Disable AI-powered insights for your family"),
        types.BotCommand(command="reason_status", description="Check AI insights status for your family"),
        types.BotCommand(command="reason_stats", description="View reasoner performance statistics (admin)"),
        # Add more as needed
    ]
    await bot.set_my_commands(commands)


async def main():
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        
        # Check dependencies
        if not check_dependencies():
            logger.error("Missing required dependencies. Exiting.")
            sys.exit(1)
        
        # Get bot token
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token or bot_token == "replace_me":
            logger.error("TELEGRAM_BOT_TOKEN not set. Please set it in .env file.")
            sys.exit(1)
        
        # Ensure directories exist
        Path("data").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)
        
        # Create bot and dispatcher
        bot = Bot(token=bot_token)
        dp = Dispatcher()
        dp.update.middleware(ProfileGateMiddleware(profiles))
        
        # Include routers (order matters - more specific routers first)
        from .onboarding import router_onboarding
        dp.include_router(router_onboarding)  # Include first for state management
        dp.include_router(router_profile)
        dp.include_router(router_insights)
        dp.include_router(router)  # Main router last (catch-all)
        
        # Start background pull loop
        asyncio.create_task(start_pull_loop(bot))
        
        # Register commands
        await set_commands(bot)
        
        # Log startup
        logger.info("Starting Silli Bot...")
        logger.info(f"PWA_HOST: {os.getenv('PWA_HOST', 'localhost:5173')}")
        logger.info(f"KEEP_RAW_MEDIA: {os.getenv('KEEP_RAW_MEDIA', 'false')}")
        
        # Log reasoner configuration
        reasoner_config = create_reasoner_config()
        logger.info(f"Reasoner enabled: {reasoner_config.enabled}")
        if reasoner_config.enabled:
            logger.info(f"Reasoner base_url: {reasoner_config.base_url}")
            logger.info(f"Reasoner model_hint: {reasoner_config.model_hint}")
            logger.info(f"Reasoner temperature: {reasoner_config.temperature}")
            logger.info(f"Reasoner timeout: {reasoner_config.timeout_s}s")
        else:
            logger.info("Reasoner disabled - AI insights will not be available")
        
        # Start polling
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("Shutting down Silli Bot...")
    except Exception as e:
        logger.error(f"Failed to start Silli Bot: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 