from typing import Any, Awaitable, Callable, Dict, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from loguru import logger
from .profiles import profiles
from .handlers_gate import show_greeting_card


class GateMiddleware(BaseMiddleware):
    """Middleware that gates all messages until user completes onboarding."""
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        # Skip middleware for callback queries (gate callbacks)
        if isinstance(event, CallbackQuery):
            return await handler(event, data)
        
        # Get user profile
        chat_id = event.chat.id
        profile = profiles.get_profile_by_chat_sync(chat_id)
        
        # If no profile exists, create one with "unlinked" status
        if not profile:
            logger.info(f"Creating new profile for chat {chat_id}")
            profiles.upsert_fields_sync(chat_id, {
                "status": "unlinked",
                "locale": "en"
            })
            profile = profiles.get_profile_by_chat_sync(chat_id)
        
        # Check if user is gated (status != "active")
        if profile and profile.get("status") != "active":
            logger.info(f"User {chat_id} is gated (status: {profile.get('status')})")
            
            # Show greeting card instead of processing the message
            await show_greeting_card(event)
            return
        
        # User is active, proceed with normal handler
        return await handler(event, data)
