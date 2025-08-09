import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Update

logger = logging.getLogger(__name__)
diag_router = Router(name="diag")

@diag_router.message()
async def _log_msg(message: Message):
    logger.info(f"🔍 [DIAG] message chat={message.chat.id} text={message.text!r}")
    # Pass through to other routers by not returning anything

@diag_router.callback_query()
async def _log_cb(cb: CallbackQuery):
    data = getattr(cb, "data", None)
    logger.info(f"🔍 [DIAG] callback chat={cb.message.chat.id if cb.message else 'n/a'} data={data!r}")
    # Pass through to other routers by not returning anything
