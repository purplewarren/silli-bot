import logging
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)
safe_enhanced = Router(name="safe_enhanced")

# Simple family data simulation (replace with real families lookup later)
def get_mock_family(chat_id):
    return {
        'family_id': f"fam_{chat_id}",
        'parent_name': "Test Parent",
        'children': ["Child 1", "Child 2"],
        'members': 2,
        'enabled_dyads': ["night_helper", "meal_mood", "tantrum_translator"],
        'cloud_reasoning': True
    }

# /start command with safe mode indicator
@safe_enhanced.message(F.text.in_({"/start", "/help"}))
async def start_help(message: Message):
    logger.info(f"📨 Safe Enhanced: /start from chat {message.chat.id}")
    try:
        await message.answer(
            "<b>🚑 Safe Mode Bot - Enhanced</b>\n\n"
            "✅ Diagnostic router active\n"
            "✅ Core commands available\n\n"
            "Commands:\n"
            "• /familyprofile - Family stats\n"
            "• /summondyad - Launch dyads\n"
            "• /reasoning - Toggle AI\n"
            "• /test - Test response\n"
            "• /help - This message"
        )
        logger.info(f"✅ Safe Enhanced: Sent /start response to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in start_help: {e}")
        await message.answer("❌ Error in enhanced safe mode bot")

# /familyprofile with mock data
@safe_enhanced.message(F.text.in_({"/family", "/familyprofile"}))
async def family_profile(message: Message):
    logger.info(f"📨 Safe Enhanced: /familyprofile from chat {message.chat.id}")
    try:
        family = get_mock_family(message.chat.id)
        
        response = (
            f"<b>👨‍👩‍👧‍👦 Family Profile</b>\n\n"
            f"<b>Family ID:</b> {family['family_id']}\n"
            f"<b>Parent:</b> {family['parent_name']}\n"
            f"<b>Children:</b> {len(family['children'])}\n"
            f"<b>Members:</b> {family['members']}\n"
            f"<b>Enabled Dyads:</b> {len(family['enabled_dyads'])}\n"
            f"<b>AI Reasoning:</b> {'✅ ON' if family['cloud_reasoning'] else '❌ OFF'}\n\n"
            f"<i>Safe mode - using mock data</i>"
        )
        
        await message.answer(response)
        logger.info(f"✅ Safe Enhanced: Sent family profile to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in family_profile: {e}")
        await message.answer("❌ Error getting family profile")

# /summondyad with mock dyads
@safe_enhanced.message(F.text == "/summondyad")
async def summon_dyad(message: Message):
    logger.info(f"📨 Safe Enhanced: /summondyad from chat {message.chat.id}")
    try:
        family = get_mock_family(message.chat.id)
        enabled_dyads = family['enabled_dyads']
        
        if not enabled_dyads:
            await message.answer("No dyads enabled yet.")
            return
        
        kb = InlineKeyboardBuilder()
        dyad_names = {
            "night_helper": "🌙 Night Helper",
            "meal_mood": "🍽️ Meal Mood Companion", 
            "tantrum_translator": "😤 Tantrum Translator"
        }
        
        for dyad_key in enabled_dyads:
            name = dyad_names.get(dyad_key, dyad_key.replace('_', ' ').title())
            kb.button(text=name, callback_data=f"safe_dyad:launch:{dyad_key}")
        
        kb.adjust(1)
        
        response = (
            f"<b>🔮 Choose a Dyad to start:</b>\n\n"
            f"<i>Safe mode - testing dyad launch</i>"
        )
        
        await message.answer(response, reply_markup=kb.as_markup())
        logger.info(f"✅ Safe Enhanced: Sent dyad list to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in summon_dyad: {e}")
        await message.answer("❌ Error listing dyads")

# /reasoning toggle
@safe_enhanced.message(F.text == "/reasoning")
async def reasoning_toggle(message: Message):
    logger.info(f"📨 Safe Enhanced: /reasoning from chat {message.chat.id}")
    try:
        # Mock toggle (in real implementation would update family data)
        await message.answer(
            "<b>🧠 AI Reasoning Toggle</b>\n\n"
            "Current: <b>✅ ON</b>\n"
            "This would toggle AI reasoning on/off.\n\n"
            "<i>Safe mode - mock toggle</i>"
        )
        logger.info(f"✅ Safe Enhanced: Sent reasoning toggle to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in reasoning_toggle: {e}")
        await message.answer("❌ Error toggling reasoning")

# Test command for verification
@safe_enhanced.message(F.text == "/test")
async def test_command(message: Message):
    logger.info(f"📨 Safe Enhanced: /test from chat {message.chat.id}")
    await message.answer("✅ Enhanced safe mode test successful!")

# Handle dyad launch callbacks
@safe_enhanced.callback_query(F.data.startswith("safe_dyad:launch:"))
async def handle_dyad_launch(callback: CallbackQuery):
    logger.info(f"📨 Safe Enhanced: dyad callback '{callback.data}' from chat {callback.message.chat.id}")
    try:
        dyad_key = callback.data.split(":", 2)[-1]
        
        # Mock PWA URL generation
        pwa_host = os.getenv("PWA_HOST", "localhost:5173")
        mock_token = "mock_jwt_token_12345"
        
        # Map dyad IDs to PWA routes
        dyad_mapping = {
            "night_helper": "night",
            "meal_mood": "meal", 
            "tantrum_translator": "tantrum"
        }
        pwa_dyad = dyad_mapping.get(dyad_key, dyad_key)
        
        url = f"https://{pwa_host}/?dyad={pwa_dyad}&token={mock_token}"
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🚀 Launch", url=url)
        kb.button(text="ℹ️ More Info", callback_data=f"safe_dyad:info:{dyad_key}")
        kb.adjust(2)
        
        response = (
            f"<b>🔮 {dyad_key.replace('_', ' ').title()} Ready</b>\n\n"
            f"Token expires in 10 minutes.\n\n"
            f"<i>Safe mode - mock JWT: {mock_token[:20]}...</i>"
        )
        
        await callback.message.edit_text(response, reply_markup=kb.as_markup())
        await callback.answer()
        logger.info(f"✅ Safe Enhanced: Sent dyad launch for {dyad_key}")
        
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in handle_dyad_launch: {e}")
        await callback.answer("❌ Error launching dyad")

# Handle dyad info callbacks
@safe_enhanced.callback_query(F.data.startswith("safe_dyad:info:"))
async def handle_dyad_info(callback: CallbackQuery):
    logger.info(f"📨 Safe Enhanced: dyad info '{callback.data}' from chat {callback.message.chat.id}")
    try:
        dyad_key = callback.data.split(":", 2)[-1]
        
        info_text = {
            "night_helper": "Helps with bedtime routines and sleep challenges.",
            "meal_mood": "Assists with mealtime behavior and food preferences.",
            "tantrum_translator": "Provides strategies for managing tantrums and emotional outbursts."
        }
        
        info = info_text.get(dyad_key, f"Information about {dyad_key.replace('_', ' ')}.")
        
        response = (
            f"<b>ℹ️ {dyad_key.replace('_', ' ').title()}</b>\n\n"
            f"{info}\n\n"
            f"<i>Safe mode - mock information</i>"
        )
        
        kb = InlineKeyboardBuilder()
        kb.button(text="🔙 Back", callback_data=f"safe_dyad:launch:{dyad_key}")
        
        await callback.message.edit_text(response, reply_markup=kb.as_markup())
        await callback.answer()
        logger.info(f"✅ Safe Enhanced: Sent dyad info for {dyad_key}")
        
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in handle_dyad_info: {e}")
        await callback.answer("❌ Error getting dyad info")

# Catch any other text
@safe_enhanced.message()
async def handle_text(message: Message):
    logger.info(f"📨 Safe Enhanced: text '{message.text}' from chat {message.chat.id}")
    try:
        await message.answer(
            f"📋 Enhanced safe mode received: <b>{message.text}</b>\n\n"
            "Try: /start, /familyprofile, /summondyad, /reasoning, /test"
        )
        logger.info(f"✅ Safe Enhanced: Sent text response to chat {message.chat.id}")
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in handle_text: {e}")
        await message.answer("❌ Error processing message")

# Handle any other callbacks
@safe_enhanced.callback_query()
async def handle_callback(callback: CallbackQuery):
    logger.info(f"📨 Safe Enhanced: callback '{callback.data}' from chat {callback.message.chat.id}")
    try:
        await callback.answer("Enhanced safe mode callback received")
        await callback.message.answer("🔘 Enhanced safe mode callback handler")
    except Exception as e:
        logger.error(f"❌ Safe Enhanced error in handle_callback: {e}")
        await callback.answer("Error in safe mode")
