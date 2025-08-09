from aiogram.dispatcher.middlewares.base import BaseMiddleware  # aiogram v3
from aiogram.types import CallbackQuery, Message
from typing import Tuple, Optional
from loguru import logger
from .profiles import profiles

ALLOWED_PREFIXES: Tuple[str, ...] = ("fs:", "dyad:", "ai:", "finish:")

class GateMiddleware(BaseMiddleware):
    """
    Blocks user interaction until family profile is active,
    but *never* blocks finish-setup callbacks (fs:/dyad:/ai:/finish:).
    """

    def __init__(self):
        super().__init__()
        self.profiles = profiles

    async def __call__(self, handler, event, data):
        from aiogram.types import Update
        
        # Extract CallbackQuery from Update if it's nested
        callback_query = None
        if isinstance(event, Update) and event.callback_query:
            callback_query = event.callback_query
        elif isinstance(event, CallbackQuery):
            callback_query = event
            
        # 1) Always pass through finish-setup callbacks
        if callback_query:
            cd = callback_query.data or ""
            logger.info(f"[DEBUG GATE] Found CallbackQuery data: {cd}")
            if cd.startswith(ALLOWED_PREFIXES):
                logger.info(f"Allowing finish-setup callback: {cd}")
                return await handler(event, data)
            else:
                logger.info(f"[DEBUG GATE] CallbackQuery NOT in allowed prefixes, allowing anyway: {cd}")
                return await handler(event, data)  # Allow all callbacks for debugging

        # 2) Allow basic commands that lead to onboarding/info
        if isinstance(event, Message) and event.text:
            tok = event.text.split()[0]
            if tok in ("/start", "/about", "/lang", "/help"):
                logger.info(f"Allowing basic command: {tok}")
                return await handler(event, data)

        # 3) Gating logic for everything else
        chat_id = None
        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = event.message.chat.id
        elif isinstance(event, Update):
            if event.message:
                chat_id = event.message.chat.id
            elif event.callback_query and event.callback_query.message:
                chat_id = event.callback_query.message.chat.id

        if chat_id is None:
            # no chat context; just allow
            logger.warning(f"No chat context for event type {type(event)}")
            if isinstance(event, CallbackQuery):
                logger.warning(f"[DEBUG] CallbackQuery with no chat: data={getattr(event, 'data', 'NO_DATA')}")
            return await handler(event, data)

        # Get family profile by chat
        profile = self.profiles.get_profile_by_chat_sync(chat_id)
        
        # If no profile exists, create one with "unlinked" status
        if not profile:
            logger.info(f"Creating new profile for chat {chat_id}")
            self.profiles.upsert_fields_sync(chat_id, {
                "status": "unlinked",
                "locale": "en"
            })
            profile = self.profiles.get_profile_by_chat_sync(chat_id)

        allowed = bool(profile and profile.get("status") == "active")

        if allowed:
            return await handler(event, data)

        # Blocked: show gate card (and ack if callback)
        logger.info(f"User {chat_id} is gated (status: {profile.get('status') if profile else 'no_profile'})")
        
        try:
            if isinstance(event, CallbackQuery):
                await event.answer("Finish setup to continue", cache_time=2)
        except Exception as e:
            logger.warning(f"Failed to answer callback: {e}")

        from .handlers_gate import show_greeting_card  # lazy import to avoid cycles
        try:
            await show_greeting_card(event)
        except Exception as e:
            logger.warning(f"Failed to show greeting card: {e}")

        # swallow the update (don't call handler)
        return
