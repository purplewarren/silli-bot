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
from aiogram.enums import ParseMode
from loguru import logger
from .handlers import router
from .puller import start_pull_loop
from aiogram import types
from .gate_middleware import GateMiddleware
from .profiles import profiles
from .handlers_profile import router_profile
from .handlers_insights import router_insights
from .reason_client import client as reasoner_client


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
    """Set a clean, minimal command list for better UX."""
    commands = [
        types.BotCommand(command="start", description="Begin onboarding"),
        types.BotCommand(command="familyprofile", description="Family dashboard"),
        types.BotCommand(command="summondyad", description="Launch helpers"),
        types.BotCommand(command="reasoning", description="Toggle AI"),
        types.BotCommand(command="help", description="All commands"),
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
        from aiogram.client.default import DefaultBotProperties
        bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        
        # Global error handler (no more silent fails)
        from aiogram.types.error_event import ErrorEvent

        @dp.errors()
        async def on_error(event: ErrorEvent):
            logger.exception("[GLOBAL ERROR] Unhandled exception", exc_info=event.exception)
            try:
                upd = event.update
                chat_id = getattr(getattr(upd, "message", None), "chat", None) and upd.message.chat.id
                if not chat_id and getattr(upd, "callback_query", None):
                    chat_id = upd.callback_query.message.chat.id
                if chat_id:
                    await bot.send_message(chat_id, "⚠️ Something went wrong. We're on it.")
            except Exception:
                pass

        # Safe-mode router implementation
        from .diag_router import diag_router
        from .routers_safe import safe
        
        # Skip diagnostic router in normal mode - it consumes all messages
        # dp.include_router(diag_router)
        # dp.include_router(safe)
        
        # Only include other routers if not in safe mode
        if os.getenv("SAFE_MODE") != "1":
            logger.info("Normal mode - including all routers")
            from .handlers_gate import router_gate
            from .handlers_onboarding import router_onboarding
            from .handlers_family_link import router_family_link
            from .handlers_family_create import router_family_create
            from .handlers_finish_setup import router_finish_setup
            from .handlers_commands import router_commands
            from .handlers_reasoner_info import router_reasoner_info
            from .handlers_i18n import router_i18n
            from .handlers_reason_debug import router_reason_debug
            
            dp.include_router(router_reason_debug)   # Debug commands - HIGHEST PRIORITY
            dp.include_router(router_finish_setup)   # has fs:/dyad:/ai: callbacks
            dp.include_router(router_commands)       # /reasoning, /familyprofile, /summondyad, etc. - HIGH PRIORITY
            dp.include_router(router_onboarding)     # /start command - Include for state management
            dp.include_router(router_family_link)    # Family linking
            dp.include_router(router_family_create)  # Family creation
            dp.include_router(router_reasoner_info)  # Reasoner info commands
            dp.include_router(router_i18n)           # Include i18n router
            dp.include_router(router_gate)           # any broad/catch-all handlers
            dp.include_router(router_profile)
            dp.include_router(router_insights)
            dp.include_router(router)  # Main router last (catch-all)
        else:
            logger.info("SAFE MODE - only diagnostic and safe routers loaded")
        
        # Start background pull loop
        asyncio.create_task(start_pull_loop(bot))
        
        # Start proactive scheduler only if not in safe mode
        if os.getenv("SAFE_MODE") != "1":
            from .scheduler import start_scheduler
            asyncio.create_task(start_scheduler())
        else:
            logger.info("SAFE MODE - scheduler disabled")
        
        # Register commands
        await set_commands(bot)
        
        # Log startup
        logger.info("Starting Silli Bot...")
        logger.info(f"PWA_HOST: {os.getenv('PWA_HOST', 'localhost:5173')}")
        logger.info(f"KEEP_RAW_MEDIA: {os.getenv('KEEP_RAW_MEDIA', 'false')}")
        
        # Log reasoner configuration
        # Log reasoner status
        reasoner_status = reasoner_client.status()
        logger.info(f"Reasoner model_hint: {reasoner_status.get('model_hint', 'unknown')}")
        logger.info(f"Reasoner model_used: {reasoner_status.get('model_used', 'unknown')}")
        logger.info(f"Reasoner base_url: {reasoner_client.base}")
        logger.info(f"Reasoner timeout: {reasoner_client.timeout}s")
        
        # Hard guarantee: delete webhook and explicitly set allowed updates
        await bot.delete_webhook(drop_pending_updates=True)
        allowed = dp.resolve_used_update_types()
        logger.info(f"[NORMAL] allowed_updates={allowed}")
        
        # Start polling
        await dp.start_polling(bot, allowed_updates=allowed)
        
    except KeyboardInterrupt:
        logger.info("Shutting down Silli Bot...")
    except Exception as e:
        logger.error(f"Failed to start Silli Bot: {e}")
        sys.exit(1)


async def _run_normal():
    # Normal startup with full bot architecture
    await main()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL","INFO")))
    
    if os.getenv("SAFE_MODE") == "1":
        from bot.safe_main import run_safe
        asyncio.run(run_safe())
    else:
        asyncio.run(_run_normal()) 