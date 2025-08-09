import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)
safe = Router(name="safe")

# /start and /help
@safe.message(F.text.in_({"/start", "/help"}))
async def start_help(message: Message):
    logger.info(f"📨 Safe router: /start from chat {message.chat.id}")
    try:
        await message.answer(
            "<b>🚀 Safe Mode Bot Active!</b>\n\n"
            "Available commands:\n"
            "• /familyprofile - Family stats\n"
            "• /summondyad - Launch dyads\n"
            "• /reasoning - Toggle AI\n"
            "• /help - This message"
        )
        logger.info(f"✅ Safe router: Sent /start response to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Safe router error in start_help: {e}")
        await message.answer("❌ Error in safe mode bot")

# Simple test command
@safe.message(F.text == "/test")
async def test_command(message: Message):
    logger.info(f"📨 Safe router: /test from chat {message.chat.id}")
    await message.answer("✅ Safe mode test successful!")

# Catch any other text
@safe.message()
async def handle_text(message: Message):
    logger.info(f"📨 Safe router: text '{message.text}' from chat {message.chat.id}")
    try:
        if message.text == "/familyprofile":
            await message.answer("👨‍👩‍👧‍👦 Family profile placeholder (safe mode)")
        elif message.text == "/summondyad":
            await message.answer("🔮 Dyad summon placeholder (safe mode)")
        elif message.text == "/reasoning":
            await message.answer("🧠 AI reasoning placeholder (safe mode)")
        else:
            await message.answer(
                f"📋 Safe mode received: {message.text}\n\n"
                "Try: /start, /test, /familyprofile, /summondyad, /reasoning"
            )
        logger.info(f"✅ Safe router: Sent response to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Safe router error in handle_text: {e}")
        await message.answer("❌ Error processing message in safe mode")

# Handle any callbacks
@safe.callback_query()
async def handle_callback(callback: CallbackQuery):
    logger.info(f"📨 Safe router: callback '{callback.data}' from chat {callback.message.chat.id}")
    try:
        await callback.answer("Safe mode callback received")
        await callback.message.answer("🔘 Safe mode callback handler")
    except Exception as e:
        logger.error(f"❌ Safe router error in handle_callback: {e}")
        await callback.answer("Error in safe mode")