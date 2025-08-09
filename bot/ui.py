from aiogram import Bot
from aiogram.types import Message
import html

async def send_thinking(bot: Bot, chat_id: int) -> None:
    """Show typing indicator while ME is working"""
    from .strings import COPY
    await bot.send_chat_action(chat_id, COPY["thinking_indicator"])

def render_tipset(tips, rationale, model_used: str) -> str:
    """Render AI response in consistent HTML format"""
    tips = [t.strip() for t in (tips or []) if t and t.strip()]
    bullet = "\n".join(f"• {html.escape(t)}" for t in tips[:3]) or "• I'm here and ready to help."
    rationale = html.escape(rationale or "")
    return (
        f"<b>Try this</b>\n{bullet}\n\n"
        f"<i>{rationale}</i>\n\n"
        f"<code>ME:{html.escape(model_used or '?')}</code>"
    )
