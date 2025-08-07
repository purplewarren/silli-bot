"""
Internationalization command handlers for Silli Bot
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger
from .i18n import get_locale, set_locale, get_supported_locales, is_supported_locale

router_i18n = Router()

@router_i18n.message(Command("lang"))
async def lang_command(message: Message):
    """Handle /lang command for language switching."""
    try:
        chat_id = message.chat.id
        args = message.text.split()
        
        if len(args) != 2:
            # Show current language and available options
            current_locale = get_locale(chat_id)
            supported = get_supported_locales()
            
            help_text = f"🌐 **Current language**: {current_locale.upper()}\n\n"
            help_text += "**Available languages**:\n"
            for locale in supported:
                flag = "🇺🇸" if locale == "en" else "🇧🇷"
                help_text += f"{flag} `{locale}`\n"
            help_text += "\n**Usage**: `/lang <locale>`\n"
            help_text += "**Example**: `/lang pt_br`"
            
            await message.reply(help_text, parse_mode="Markdown")
            return
        
        # Set new language
        new_locale = args[1].lower()
        
        if not is_supported_locale(new_locale):
            await message.reply(
                f"❌ Unsupported language: `{new_locale}`\n\n"
                f"Supported: {', '.join(get_supported_locales())}",
                parse_mode="Markdown"
            )
            return
        
        # Update locale
        success = set_locale(chat_id, new_locale)
        
        if success:
            # Reply in the new language
            if new_locale == "pt_br":
                reply_text = f"✅ **Idioma alterado para**: {new_locale.upper()}\n\n"
                reply_text += "Agora todas as mensagens do bot aparecerão em português brasileiro."
            else:
                reply_text = f"✅ **Language changed to**: {new_locale.upper()}\n\n"
                reply_text += "All bot messages will now appear in English."
            
            await message.reply(reply_text, parse_mode="Markdown")
            
            logger.info(f"Language changed to {new_locale} for chat {chat_id}")
        else:
            await message.reply("❌ Failed to change language. Please try again.")
            
    except Exception as e:
        logger.error(f"Error in lang command: {e}")
        await message.reply("❌ An error occurred while changing language.")
