import os, asyncio, logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# minimal, no middleware, HTML mode + diag + safe routers
async def run_safe():
    load_dotenv()
    logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL","INFO")))
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    assert token, "TELEGRAM_BOT_TOKEN missing"

    bot = Bot(token=token, parse_mode="HTML")
    dp = Dispatcher()
    
    # Include diagnostic router for logging
    from bot.diag_router import diag_router
    dp.include_router(diag_router)
    
    # Include enhanced safe router with core functionality
    from bot.routers_safe_enhanced import safe_enhanced
    dp.include_router(safe_enhanced)

    # Fallback handlers for testing
    @dp.message(F.text == "/start")
    async def start_fallback(m: Message):
        await m.answer("🚑 Safe-mode online. Core path restored.")

    @dp.message()
    async def any_msg_fallback(m: Message):
        await m.answer(f"🛰️ Fallback received: <b>{m.text}</b>")

    @dp.callback_query()
    async def any_cb_fallback(cb: CallbackQuery):
        await cb.answer("ok")

    # hard guarantee: delete webhook and explicitly set allowed updates
    await bot.delete_webhook(drop_pending_updates=True)
    allowed = dp.resolve_used_update_types()
    logging.info(f"[SAFE] allowed_updates={allowed}")

    await dp.start_polling(bot, allowed_updates=allowed)
