import asyncio
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from typing import List
from bot.profiles import profiles, Child
from bot.storage import Storage, EventRecord
from datetime import datetime
from loguru import logger

# ========== STORAGE INSTANCE ==========
storage = Storage()

# ========== STATES ==========
class Onboarding(StatesGroup):
    waiting_for_consent = State()
    waiting_for_family_choice = State()
    waiting_for_new_family_name = State()
    waiting_for_family_id = State()
    verifying_2fa = State()

# ========== ROUTER ==========
router_onboarding = Router()

# ========== INLINE BUTTONS ==========
def consent_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Accept", callback_data="accept_consent")],
        [InlineKeyboardButton(text="Decline", callback_data="decline_consent")]
    ])

def family_choice_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Create New Family Profile", callback_data="create_family")]
    ])

# ========== /START HANDLER ==========
@router_onboarding.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """Handle /start command with consent flow."""
    try:
        family_id = f"fam_{message.chat.id}"
        
        await state.set_state(Onboarding.waiting_for_consent)
        
        consent_text = (
            "👋 Welcome. Silli ME helps parents take better care of their children.\n\n"
            "To proceed, please review and accept our [Privacy Policy](https://gist.github.com/example-privacy).\n\n"
            "🛡️ Silli only processes derived data — never raw audio or video.\n\n"
            "Do you accept?"
        )
        
        await message.answer(
            consent_text,
            reply_markup=consent_buttons(),
            parse_mode="Markdown"
        )
        
        # Log onboarding start event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_onboarding_start_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="onboarding",
            actor="parent",
            event="onboarding_start",
            labels=["silli_introduced"]
        )
        storage.append_event(event)
        
        logger.info(f"Onboarding started for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")

# ========== CONSENT CALLBACKS ==========
@router_onboarding.callback_query(F.data == "decline_consent")
async def handle_decline(callback: CallbackQuery, state: FSMContext):
    """Handle consent decline."""
    try:
        family_id = f"fam_{callback.message.chat.id}"
        
        await callback.message.edit_text(
            "Understood. You can return anytime to continue. Type /start to begin again."
        )
        await state.clear()
        
        # Log consent declined event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_consent_declined_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="consent",
            actor="parent",
            event="consent_declined",
            labels=["consent_declined"]
        )
        storage.append_event(event)
        
        logger.info(f"Consent declined for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in decline consent: {e}")
        await callback.answer("Error occurred", show_alert=True)

@router_onboarding.callback_query(F.data == "accept_consent")
async def handle_accept(callback: CallbackQuery, state: FSMContext):
    """Handle consent acceptance."""
    try:
        family_id = f"fam_{callback.message.chat.id}"
        
        await state.set_state(Onboarding.waiting_for_family_choice)
        
        welcome_text = (
            "✅ You're in. Welcome to Silli.\n\n"
            "Let's create your Family Profile.\n\n"
            "If you're joining an existing family, just send your Silli Family ID now.\n"
            "Otherwise, tap below to start fresh."
        )
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=family_choice_buttons()
        )
        
        # Log consent accepted event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_consent_accepted_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="consent",
            actor="parent",
            event="consent_accepted",
            labels=["consent_granted"]
        )
        storage.append_event(event)
        
        logger.info(f"Consent accepted for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in accept consent: {e}")
        await callback.answer("Error occurred", show_alert=True)

# ========== NEW FAMILY FLOW ==========
@router_onboarding.callback_query(F.data == "create_family")
async def ask_family_name(callback: CallbackQuery, state: FSMContext):
    """Ask for new family name."""
    try:
        await state.set_state(Onboarding.waiting_for_new_family_name)
        await callback.message.edit_text(
            "What would you like to call your Family Profile? (e.g., 'Barakat Home')"
        )
        
    except Exception as e:
        logger.error(f"Error in create family: {e}")
        await callback.answer("Error occurred", show_alert=True)

@router_onboarding.message(Onboarding.waiting_for_new_family_name)
async def save_family_name(message: Message, state: FSMContext):
    """Save family name and proceed to verification."""
    try:
        family_id = f"fam_{message.chat.id}"
        family_name = message.text.strip()
        
        if not family_name or len(family_name) < 2:
            await message.reply("Please enter a valid family name (at least 2 characters).")
            return
        
        await state.update_data(family_name=family_name)
        await state.set_state(Onboarding.verifying_2fa)
        
        # Create basic profile
        profile_data = {
            "family_id": family_id,
            "family_name": family_name,
            "parent_name": None,
            "parent_age": None,
            "timezone": "UTC",
            "children": [],
            "health_notes": "",
            "lifestyle_tags": [],
            "complete": False,
            "created_at": datetime.now().isoformat()
        }
        
        profiles.upsert_profile(profile_data)
        
        await message.answer(
            f"Great. We've created your Family Profile: \"{family_name}\".\n\n"
            "Now verifying your phone number…"
        )
        
        # Simulate phone verification (placeholder)
        await asyncio.sleep(2)
        
        # Mark profile as complete
        profiles.upsert_fields(family_id, {"complete": True})
        
        await message.answer(
            f"✅ Done. You're now the first member of \"{family_name}\".\n\n"
            "You can now:\n"
            "• Summon a helper (/summon_helper)\n"
            "• Send a voice note (/analyze)\n"
            "• Review sessions (/list)"
        )
        
        await state.clear()
        
        # Log family creation event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_family_created_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="onboarding",
            actor="parent",
            event="family_created",
            labels=["new_family", "profile_complete"]
        )
        storage.append_event(event)
        
        logger.info(f"Family created: {family_name} for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in save family name: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")

# ========== EXISTING FAMILY FLOW ==========
@router_onboarding.message(Onboarding.waiting_for_family_choice)
async def receive_family_id(message: Message, state: FSMContext):
    """Handle existing family ID input."""
    try:
        family_id = f"fam_{message.chat.id}"
        input_family_id = message.text.strip()
        
        # Basic validation (placeholder - should validate against existing families)
        if not input_family_id or len(input_family_id) < 3:
            await message.reply("Please enter a valid Family ID.")
            return
        
        await state.set_state(Onboarding.verifying_2fa)
        
        await message.answer(
            f"Trying to join Family ID: {input_family_id}.\n"
            "Verifying your phone number…"
        )
        
        # Simulate phone verification (placeholder)
        await asyncio.sleep(2)
        
        # For now, just create a basic profile (in real implementation, would link to existing)
        profile_data = {
            "family_id": family_id,
            "family_name": f"Family {input_family_id}",
            "parent_name": None,
            "parent_age": None,
            "timezone": "UTC",
            "children": [],
            "health_notes": "",
            "lifestyle_tags": [],
            "complete": True,
            "created_at": datetime.now().isoformat()
        }
        
        profiles.upsert_profile(profile_data)
        
        await message.answer(
            f"✅ You're now linked to \"{input_family_id}\".\n\n"
            "You can now:\n"
            "• Summon a helper (/summon_helper)\n"
            "• Send a voice note (/analyze)\n"
            "• Review sessions (/list)"
        )
        
        await state.clear()
        
        # Log family join event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_family_joined_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="onboarding",
            actor="parent",
            event="family_joined",
            labels=["existing_family", "profile_complete"]
        )
        storage.append_event(event)
        
        logger.info(f"Family joined: {input_family_id} by {family_id}")
        
    except Exception as e:
        logger.error(f"Error in receive family id: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")

# ========== PROTECT FEATURES ==========
@router_onboarding.message()
async def protect_features(message: Message, state: FSMContext):
    """Protect features for users who haven't completed onboarding."""
    current_state = await state.get_state()
    if current_state and current_state.startswith("Onboarding"):
        await message.reply("🔐 Please finish onboarding first. Type /start to begin.")
    else:
        await message.reply("Unrecognized command. Type /help for options.")

# ========== CANCEL ONBOARDING ==========
@router_onboarding.message(Command("cancel"))
async def cancel_onboarding(message: Message, state: FSMContext):
    """Cancel onboarding process."""
    try:
        family_id = f"fam_{message.chat.id}"
        
        await state.clear()
        await message.reply(
            "Onboarding cancelled. Type /start to begin again."
        )
        
        # Log cancellation event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_onboarding_cancelled_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="onboarding",
            actor="parent",
            event="onboarding_cancelled",
            labels=["cancelled"]
        )
        storage.append_event(event)
        
        logger.info(f"Onboarding cancelled for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in cancel onboarding: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")