from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from .insights import compute_insights
from .storage import Storage
from .families import FamiliesStore
from loguru import logger

router_insights = Router()
storage = Storage()
families = FamiliesStore()

@router_insights.message(Command("insights"))
async def insights_command(message: Message):
    """Handle /insights command - show AI-aided insights from sessions."""
    try:
        family_id = f"fam_{message.chat.id}"
        events = storage.get_events(family_id)
        
        if not events:
            await message.reply("No sessions yet. Try a few voice notes or PWA sessions first.")
            return
        
        insights = compute_insights(events)
        
        # Build response with ≤3 calm bullets
        lines = []
        
        if insights.get('night') and insights['night'] != '—':
            lines.append(f"🌙 **Night**: {insights['night']}")
        
        if insights.get('tantrum') and insights['tantrum'] != '—':
            lines.append(f"😤 **Tantrum**: {insights['tantrum']}")
        
        if insights.get('meal') and insights['meal'] != '—':
            lines.append(f"🍽 **Meal**: {insights['meal']}")
        
        if not lines:
            lines = ["No insights yet. Try a few sessions with different helpers."]
        
        # Ensure we don't exceed 3 lines
        response_lines = lines[:3]
        response = "\n".join(response_lines)
        
        await message.reply(
            f"**Your AI-Aided Insights** (last 7 days):\n\n{response}",
            parse_mode="Markdown"
        )
        
        logger.info(f"Insights requested for family {family_id}, returned {len(response_lines)} insights")
        
    except Exception as e:
        logger.error(f"Error in insights command: {e}")
        await message.reply("Sorry, I couldn't generate insights right now. Please try again.")