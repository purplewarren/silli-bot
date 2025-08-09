"""
Centralized strings and microcopy for Silli ME Bot
Maintains consistent tone: brief, calm, helpful, privacy-forward
"""

BRAND_NAME = "Silli ME"

COPY = {
    "busy": "ME is thinking… I'll be right back.",
    "retry": "ME is busy for a moment – please try again shortly.",
    "help_header": "<b>How I can help</b>\n• Sleep struggles\n• Tantrums & behaviors\n• Mealtime stress\n\nType what's going on.",
    
    # Additional consistent messaging
    "timeout_fallback": "ME is taking longer than usual. Try asking about specific parenting challenges!",
    "error_fallback": "ME is having trouble right now. Try asking a specific parenting question!",
    "circuit_open": "ME is busy for a moment—try again in ~1 min.",
    
    # Help and guidance
    "family_required": "Please complete family setup first to chat with ME.",
    "ai_disabled": "ME conversations are off. Use /reasoning to enable, or try /summondyad for helpers.",
    
    # Common responses
    "thinking_indicator": "typing",  # for send_chat_action
}
