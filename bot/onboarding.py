import asyncio
from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from typing import List
from bot.profiles import profiles, Child
from loguru import logger

# ========== STATES ==========
class OnboardStates(StatesGroup):
    AskParentName = State()
    AskParentAge = State()
    AskTimezone = State()
    AskChildName = State()
    AskChildAge = State()
    AskChildSex = State()
    AskAddAnotherChild = State()
    AskHealthNotes = State()
    AskLifestyleTags = State()
    Confirm = State()

# ========== ROUTER ==========
router_onboarding = Router()

# ========== CONSTANTS ==========
TIMEZONES = [
    "America/Sao_Paulo",
    "America/New_York",
    "Europe/London",
    "Europe/Berlin",
    "Asia/Tokyo",
    "UTC"
]
SEX_LABELS = {"m": "Boy", "f": "Girl", "na": "N/A"}

# ========== HANDLERS ==========
@router_onboarding.message(Command("onboard"))
async def start_onboarding(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(OnboardStates.AskParentName)
    await message.reply(
        "Let's set up your Family Profile.\n\nWhat's your first name?",
    )

@router_onboarding.message(OnboardStates.AskParentName)
async def ask_parent_age(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) < 2:
        await message.reply("Please enter a valid name.")
        return
    await state.update_data(parent_name=name)
    await state.set_state(OnboardStates.AskParentAge)
    await message.reply("How old are you? (optional, send a number or skip)")

@router_onboarding.message(OnboardStates.AskParentAge)
async def ask_timezone(message: Message, state: FSMContext):
    text = message.text.strip()
    age = None
    if text.isdigit():
        age = int(text)
        if not (12 <= age <= 100):
            await message.reply("Please enter a reasonable age (12-100), or skip.")
            return
    await state.update_data(parent_age=age)
    await state.set_state(OnboardStates.AskTimezone)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=tz, callback_data=f"tz:{tz}")] for tz in TIMEZONES]
    )
    await message.reply("Pick your timezone:", reply_markup=kb)

@router_onboarding.callback_query(F.data.startswith("tz:"), OnboardStates.AskTimezone)
async def ask_child_name(cb: CallbackQuery, state: FSMContext):
    tz = cb.data.split(":", 1)[1]
    await state.update_data(timezone=tz)
    await state.set_state(OnboardStates.AskChildName)
    await cb.message.edit_text(f"Timezone set to {tz}.\n\nWhat's your child's first name?")
    await cb.answer()

@router_onboarding.message(OnboardStates.AskChildName)
async def ask_child_age(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name or len(name) < 2:
        await message.reply("Please enter a valid name.")
        return
    await state.update_data(child_name=name)
    await state.set_state(OnboardStates.AskChildAge)
    await message.reply(f"How old is {name}? (years, e.g. 4.5)")

@router_onboarding.message(OnboardStates.AskChildAge)
async def ask_child_sex(message: Message, state: FSMContext):
    try:
        age = float(message.text.strip())
        if not (0 < age < 25):
            await message.reply("Please enter a reasonable age (0-25). Try again.")
            return
    except Exception:
        await message.reply("Please enter a number, e.g. 4.5")
        return
    await state.update_data(child_age=age)
    await state.set_state(OnboardStates.AskChildSex)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Boy", callback_data="sex:m"),
             InlineKeyboardButton(text="Girl", callback_data="sex:f"),
             InlineKeyboardButton(text="N/A", callback_data="sex:na")]
        ]
    )
    await message.reply("Select your child's sex:", reply_markup=kb)

@router_onboarding.callback_query(F.data.startswith("sex:"), OnboardStates.AskChildSex)
async def ask_add_another_child(cb: CallbackQuery, state: FSMContext):
    sex = cb.data.split(":", 1)[1]
    data = await state.get_data()
    child = Child(
        name=data["child_name"],
        age_years=data["child_age"],
        sex=sex
    )
    children: List[Child] = data.get("children", [])
    children.append(child)
    await state.update_data(children=children)
    await state.set_state(OnboardStates.AskAddAnotherChild)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Add another child", callback_data="add_child:yes")],
            [InlineKeyboardButton(text="Continue", callback_data="add_child:no")]
        ]
    )
    await cb.message.edit_text(
        f"Added {child.name} ({child.age_years}y, {SEX_LABELS[sex]}).\n\nAdd another child?",
        reply_markup=kb
    )
    await cb.answer()

@router_onboarding.callback_query(F.data.startswith("add_child:"), OnboardStates.AskAddAnotherChild)
async def add_another_child(cb: CallbackQuery, state: FSMContext):
    if cb.data.endswith(":yes"):
        await state.set_state(OnboardStates.AskChildName)
        await cb.message.edit_text("What's your next child's first name?")
    else:
        await state.set_state(OnboardStates.AskHealthNotes)
        await cb.message.edit_text("Any health notes? (optional, or skip)")
    await cb.answer()

@router_onboarding.message(OnboardStates.AskHealthNotes)
async def ask_lifestyle_tags(message: Message, state: FSMContext):
    notes = message.text.strip()
    await state.update_data(health_notes=notes)
    await state.set_state(OnboardStates.AskLifestyleTags)
    await message.reply("Any lifestyle tags? (comma-separated, e.g. vegetarian, outdoor_activities)\nOr skip.")

@router_onboarding.message(OnboardStates.AskLifestyleTags)
async def confirm(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    
    # Handle different input formats
    if text in ["skip", "none", "no", ""]:
        tags = []
    elif "," in text:
        # Comma-separated tags
        tags = [t.strip() for t in text.split(",") if t.strip()]
    else:
        # Single tag
        tags = [text] if text else []
    
    await state.update_data(lifestyle_tags=tags)
    await state.set_state(OnboardStates.Confirm)
    data = await state.get_data()
    
    # Enhanced summary with lifestyle tags
    summary = f"Profile summary:\n\n👤 {data.get('parent_name','')}\nTimezone: {data.get('timezone','UTC')}\nChildren: {', '.join([c.name for c in data.get('children',[])])}"
    if tags:
        summary += f"\nLifestyle: {', '.join(tags)}"
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Finish & Open Dyads", callback_data="confirm:yes")
        ]]
    )
    await message.reply(summary, reply_markup=kb)

@router_onboarding.callback_query(F.data=="confirm:yes")
async def finish(cb: CallbackQuery, state: FSMContext):
    logger.info(f"Finish callback triggered for chat {cb.message.chat.id}")
    try:
        data = await state.get_data()
        chat_id = cb.message.chat.id
        logger.info(f"State data: {data}")
        
        if not data.get("children"):
            await cb.message.edit_text("You must add at least one child.")
            await state.set_state(OnboardStates.AskChildName)
            return
        
        # Create or get profile first, then update fields
        logger.info(f"Creating/getting profile for chat {chat_id}")
        try:
            # Use a simpler approach - just create the family_id directly
            family_id = f"fam_{chat_id}"
            logger.info(f"Using family_id: {family_id}")
            
            # Check if profile already exists
            existing_profile = await profiles.get_profile_by_chat(chat_id)
            if existing_profile:
                logger.info(f"Profile already exists: {existing_profile.family_id}")
            else:
                logger.info("Profile doesn't exist, will create during upsert")
        except Exception as e:
            logger.error(f"Error creating profile: {e}")
            await cb.answer(f"Error creating profile: {str(e)}", show_alert=True)
            return
        
        try:
            # First, ensure the profile exists
            if not existing_profile:
                logger.info(f"Creating profile for {family_id}")
                # Create a minimal profile manually
                minimal_profile = profiles._create_minimal_profile(chat_id)
                # Add it to the index manually
                profiles._index[family_id] = minimal_profile
                profiles._save_index()
                logger.info(f"Minimal profile created manually: {minimal_profile.family_id}")
            
            # Now update the fields
            await profiles.upsert_fields(
                family_id,
                parent_name=data.get("parent_name",""),
                parent_age=data.get("parent_age"),
                timezone=data.get("timezone","UTC"),
                children=data.get("children",[]),
                health_notes=data.get("health_notes",""),
                lifestyle_tags=data.get("lifestyle_tags",[])
            )
            logger.info(f"Profile fields updated for {family_id}")
        except Exception as e:
            logger.error(f"Error updating profile fields: {e}")
            await cb.answer(f"Error updating profile: {str(e)}", show_alert=True)
            return
        
        await profiles.mark_complete(family_id, True)
        logger.info(f"Profile marked complete for {family_id}")
        
        await state.clear()
        await cb.message.edit_text(
            "Profile saved. You can now use Silli's helpers.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Open Dyads", callback_data="open_dyads")]]
            )
        )
        await cb.answer()
        logger.info(f"Onboarding completed successfully for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in finish callback: {e}")
        await cb.answer(f"Error: {str(e)}", show_alert=True)

@router_onboarding.callback_query(F.data=="open_dyads")
async def open_dyads(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("Use /dyads to open the helpers.")
    await cb.answer()

# Debug handler to catch any unhandled callback queries (only for onboarding-specific callbacks)
@router_onboarding.callback_query(lambda cb: cb.data.startswith(("confirm:", "open_dyads", "tz:", "sex:", "add_child:")))
async def debug_callback(cb: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    logger.warning(f"Unhandled onboarding callback query: {cb.data} from chat {cb.message.chat.id}, current state: {current_state}")
    await cb.answer(f"Debug: Received callback '{cb.data}' in state '{current_state}'", show_alert=True)

@router_onboarding.message(Command("cancel"))
async def cancel_onboarding(message: Message, state: FSMContext):
    await state.clear()
    await message.reply("Onboarding cancelled.")