import os
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher.flags import get_flag
from bot.profiles import ProfilesStore
from loguru import logger

class ProfileGateMiddleware(BaseMiddleware):
    def __init__(self, profiles_store: ProfilesStore, require_profile: bool = True):
        super().__init__()
        self.profiles_store = profiles_store
        self.require_profile = require_profile
        self.allowed_commands = [
            "/start", "/help", "/onboard", "/version", "/health", "/privacy_offline"
        ]

    async def __call__(self, handler, event, data):
        if not self.require_profile:
            return await handler(event, data)

        chat_id = None
        text = None
        if isinstance(event, Message):
            chat_id = event.chat.id
            text = event.text or ""
        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id
            text = event.data or ""
        else:
            return await handler(event, data)

        # Allow certain commands always
        if text.startswith(tuple(self.allowed_commands)):
            return await handler(event, data)

        # Check profile
        profile = await self.profiles_store.get_profile_by_chat(chat_id)
        if not profile or not profile.complete:
            logger.info(f"ProfileGate: blocking chat {chat_id} (profile incomplete)")
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Start Onboarding", callback_data="/onboard")]]
            )
            if isinstance(event, Message):
                await event.reply(
                    "Let’s finish your family profile first. Tap to start.",
                    reply_markup=kb
                )
            elif isinstance(event, CallbackQuery):
                await event.message.reply(
                    "Let’s finish your family profile first. Tap to start.",
                    reply_markup=kb
                )
                await event.answer()
            return  # Cancel handler execution by returning early
        return await handler(event, data)