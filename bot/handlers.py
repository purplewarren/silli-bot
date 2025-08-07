"""
Command and media handlers for Silli Bot
"""

import os
import json
import tempfile
import asyncio
import time
from datetime import datetime
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, Voice, PhotoSize, Video, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from loguru import logger
from .models import EventRecord, FeatureSummary, PwaSessionReport
from .i18n import get_locale
from .storage import Storage
from .analysis_audio import process_voice_note
from .wt_utils import (
    mint_autoingest_token,
    build_pwa_deeplink,
    redact_url_token,
    get_env,
)
from .families import FamiliesStore
from .reason_client import create_reasoner_config, ReasonClient, ReasonerUnavailable, clamp_metric_overrides, truncate_tips
from .dyad_registry import dyad_registry
from .utils import convert_pwa_to_bot_format, extract_dyad_label
from .profiles import profiles
from .analysis_image import analyze_photo, get_lighting_tip
from .analysis_video import analyze_video, get_motion_tip
from .cards import render_summary_card

APP_VERSION = "v0.2.0-beta"
STARTED_AT = datetime.now()

# Concurrency control for voice processing
VOICE_SEM = asyncio.Semaphore(2)

# Simple in-memory tracker for last voice session
LAST_SESSION = {}

# Store message IDs for voice messages to enable replies
VOICE_MESSAGE_IDS = {}

# ========== STORAGE INSTANCE ==========
storage = Storage()

# ========== CONSTANTS ==========
PWA_HOST = os.getenv("PWA_HOST", "purplewarren.github.io")

# ========== ROUTER ==========
router = Router()

# ========== HELPER FUNCTIONS ==========
def summarize_last_events(family_id: str, limit: int = 5) -> list:
    """
    Return a compact list of recent events for reasoning context
    
    Args:
        family_id: Family identifier
        limit: Maximum number of events to return
        
    Returns:
        List of compact event summaries
    """
    try:
        events = storage.get_events(family_id)
        # Get recent events, excluding the current one being processed
        recent_events = sorted(events, key=lambda e: e.ts, reverse=True)[:limit]
        
        summaries = []
        for event in recent_events:
            summary = {
                "ts": event.ts.isoformat(),
                "dyad": extract_dyad_label(event.labels or []),
                "event": event.event
            }
            
            # Add score if available
            if event.score is not None:
                summary["score"] = event.score
            
            # Add metrics if available (sanitized)
            if event.metrics:
                clean_metrics = {}
                for key, value in event.metrics.items():
                    if isinstance(value, (int, float, str)) and not any(skip in key.lower() for skip in ["raw", "data", "base64", "image"]):
                        clean_metrics[key] = value
                if clean_metrics:
                    summary["metrics"] = clean_metrics
            
            summaries.append(summary)
        
        return summaries
    except Exception as e:
        logger.warning(f"Error summarizing events for {family_id}: {e}")
        return []

def sanitize_for_reasoner(data: dict) -> dict:
    """
    Sanitize data for reasoner consumption
    
    Args:
        data: Input data dictionary
        
    Returns:
        Sanitized data dictionary
    """
    if not isinstance(data, dict):
        return {}
    
    sanitized = {}
    for key, value in data.items():
        # Skip raw media data
        if (key.startswith("raw_") or 
            key.endswith("_data") or 
            "base64" in key.lower() or 
            "imageData" in key):
            continue
        
        # Handle nested dictionaries
        if isinstance(value, dict):
            sanitized[key] = sanitize_for_reasoner(value)
        # Handle lists
        elif isinstance(value, list):
            sanitized[key] = [sanitize_for_reasoner(item) if isinstance(item, dict) else item for item in value]
        # Handle strings (cap length)
        elif isinstance(value, str):
            sanitized[key] = value[:300] if len(value) > 300 else value
        # Keep other types as-is
        else:
            sanitized[key] = value
    
    return sanitized

def redact_pii_context(context: dict) -> dict:
    """
    Redact PII from context data
    
    Args:
        context: Context dictionary
        
    Returns:
        Context with PII redacted
    """
    if not isinstance(context, dict):
        return {}
    
    pii_keys = ["name", "child_name", "email", "phone"]
    redacted = context.copy()
    
    for key in pii_keys:
        if key in redacted:
            redacted[key] = "[REDACTED]"
    
    return redacted

async def check_onboarding_complete(message: Message) -> bool:
    """Check if user has completed onboarding."""
    try:
        family_id = f"fam_{message.chat.id}"
        profile = await profiles.get_profile_by_chat(message.chat.id)
        
        if not profile or not profile.get("complete", False):
            await message.reply(
                "🔐 Please complete onboarding first. Type /start to begin."
            )
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking onboarding status: {e}")
        await message.reply("Error checking status. Please try /start again.")
        return False

# ========== DYAD INVOCATION SYSTEM ==========
def create_dyad_invocation_kb(dyad_id: str, language: str = "en") -> InlineKeyboardMarkup:
    """Create keyboard for Dyad invocation."""
    dyad = dyad_registry.get_dyad(dyad_id)
    if not dyad:
        return InlineKeyboardMarkup(inline_keyboard=[])
    
    launch_text = dyad_registry.get_dyad_text(dyad_id, "launch_cta", language)
    info_text = dyad_registry.get_dyad_text(dyad_id, "more_info_cta", language)
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=launch_text, callback_data=f"dyad_launch:{dyad_id}")],
        [InlineKeyboardButton(text=info_text, callback_data=f"dyad_info:{dyad_id}")]
    ])

# ========== COMMAND HANDLERS ==========
@router.message(Command("night_helper"))
async def night_helper_command(message: Message):
    """Handle night helper summoning."""
    if not await check_onboarding_complete(message):
        return
        
    try:
        family_id = f"fam_{message.chat.id}"
        
        response_text = (
            "Let's wind things down.\n\n"
            "When you're ready, I'll listen to the room.\n"
            "I won't store or upload anything — it stays on your device.\n\n"
            "Tap below to open the helper:\n\n"
            "🔗 Open Night Helper"
        )
        
        await message.reply(response_text)
        
        # Log night helper summon
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_night_helper_summoned_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="helper",
            actor="parent",
            event="night_helper_summoned",
            labels=["night_helper"]
        )
        storage.append_event(event)
        
        logger.info(f"Night helper summoned for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in night helper command: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")


@router.message(Command("tantrum_translator"))
async def tantrum_translator_command(message: Message):
    """Handle tantrum translator summoning."""
    try:
        family_id = f"fam_{message.chat.id}"
        
        response_text = (
            "I'm here.\n\n"
            "Just send a short voice note (30–60 seconds), or type a quick summary of what happened.\n\n"
            "I'll help translate what they might be feeling — and what you can try next."
        )
        
        await message.reply(response_text)
        
        # Log tantrum translator summon
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_tantrum_translator_{datetime.now().strftime('%Y%m%d_%H%M')}",
            phase="dyad_summon",
            actor="parent",
            event="tantrum_translator_summoned",
            labels=["tantrum", "emotional_support"]
        )
        storage.append_event(event)
        
        logger.info(f"Tantrum translator summoned for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in tantrum_translator command: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")


@router.message(Command("meal_mood"))
async def meal_mood_command(message: Message):
    """Handle meal mood companion summoning."""
    try:
        family_id = f"fam_{message.chat.id}"
        
        response_text = (
            "Feeding a tiny human is no small task.\n\n"
            "Want to reflect on the last meal?\n"
            "Send me a short voice note or just describe what happened."
        )
        
        await message.reply(response_text)
        
        # Log meal mood summon
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_meal_mood_{datetime.now().strftime('%Y%m%d_%H%M')}",
            phase="dyad_summon",
            actor="parent",
            event="meal_mood_summoned",
            labels=["feeding", "meal_support"]
        )
        storage.append_event(event)
        
        logger.info(f"Meal mood companion summoned for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in meal_mood command: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")


def _dyad_kb():
    """Create inline keyboard for Dyad selection."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛏 Night Helper", callback_data="dyad:night"),
        InlineKeyboardButton(text="😤 Tantrum Translator", callback_data="dyad:tantrum"),
        InlineKeyboardButton(text="🍽 Meal Companion", callback_data="dyad:meal"),
    ]])


@router.callback_query(F.data.startswith("dyad:"))
async def choose_dyad_cb(q: CallbackQuery):
    """Handle Dyad selection callback."""
    try:
        dyad = q.data.split(":")[1]  # night|tantrum|meal
        family_id = f"fam_{q.message.chat.id}"
        session_id = f"{family_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        from .wt_utils import mint_autoingest_token, build_pwa_deeplink, get_env
        relay_secret = get_env("RELAY_SECRET")
        tok = mint_autoingest_token(
            chat_id=q.message.chat.id,
            family_id=family_id,
            session_id=session_id,
            ttl_sec=30*60,
            relay_secret=relay_secret,
        )
        link = build_pwa_deeplink(
            pwa_host=get_env("PWA_HOST","localhost:5173"),
            pwa_path=get_env("PWA_PATH",""),
            mode="helper",
            family_id=family_id,
            session_id=session_id,
            token=tok,
            dyad=dyad,   # NEW
        )
        
        dyad_names = {
            "night": "Night Helper",
            "tantrum": "Tantrum Translator", 
            "meal": "Meal Mood Companion"
        }
        
        await q.message.edit_text(
            f"📱 {dyad_names[dyad]} is ready.\n"
            f"When you tap Start, your phone will listen locally for a few minutes and compute a score.\n"
            f"Privacy: no raw audio leaves the device.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=f"Start {dyad_names[dyad]}", url=link)
            ]])
        )
        
        # Log dyad summon
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=session_id,
            phase="dyad_summon",
            actor="parent",
            event="dyad_summoned",
            labels=[f"dyad:{dyad}"]
        )
        storage.append_event(event)
        
        logger.info(f"Dyad {dyad} summoned for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in choose_dyad_cb: {e}")
        await q.message.edit_text("Sorry, something went wrong. Try again.")


@router.message(Command("dyads"))
async def dyads_command(message: Message):
    """Handle /dyads command - show available helpers."""
    try:
        family_id = f"fam_{message.chat.id}"
        
        dyads_text = "Here are your Silli helpers:\n\n"
        dyads = dyad_registry.get_all_dyads()
        
        for dyad_id, dyad in dyads.items():
            icon = dyad.get("icon", "🔧")
            name = dyad.get("name", dyad_id)
            purpose = dyad.get("purpose", "")
            dyads_text += f"{icon} **{name}**\n{purpose}\n\n"
        
        await message.reply(dyads_text, reply_markup=_dyad_kb(), parse_mode="Markdown")
        
        # Log dyads command event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_dyads_command_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="helper",
            actor="parent",
            event="dyads_command",
            labels=["dyads_listed"]
        )
        storage.append_event(event)
        
        logger.info(f"Dyads command requested for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in dyads command: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")


@router.message(Command("help"))
async def help_command(message: Message):
    locale = get_locale(message.chat.id)
    
    if locale == "pt_br":
        help_text = (
            "✨ Silli AI — Seu Companheiro de Paternidade\n\n"
            "**Comandos Principais:**\n"
            "• /start — iniciar onboarding\n"
            "• /help — mostrar esta mensagem\n"
            "• /lang — alterar idioma (en/pt_br)\n"
            "• /about — re-executar apresentação\n"
            "• /insights — ver insights recentes\n"
            "• /reasoning — ativar/desativar IA\n"
            "• /familyprofile — perfil da família\n"
            "• /summondyad — listar Dyads ativos\n"
            "• /feedback — enviar feedback\n"
            "• /scheduler — status do agendador\n"
            "• /more — ver todos os comandos\n\n"
            "**Como Usar:**\n"
            "Digite naturalmente — Vou sugerir um ajudante se puder.\n"
            "Use /more para ver comandos avançados."
        )
    else:
        help_text = (
            "✨ Silli AI — Your Parenting Companion\n\n"
            "**Core Commands:**\n"
            "• /start — start onboarding\n"
            "• /help — show this message\n"
            "• /lang — change language (en/pt_br)\n"
            "• /about — re-run introduction\n"
            "• /insights — view recent insights\n"
            "• /reasoning — toggle AI on/off\n"
            "• /familyprofile — family profile\n"
            "• /summondyad — list active Dyads\n"
            "• /feedback — send feedback\n"
            "• /scheduler — scheduler status\n"
            "• /more — see all commands\n\n"
            "**How to Use:**\n"
            "Type naturally — I'll suggest a helper if I can.\n"
            "Use /more to see advanced commands."
        )
    
    await message.reply(help_text, parse_mode="Markdown")


@router.message(Command("version"))
async def version_cmd(message: Message):
    await message.reply(f"Silli Bot {APP_VERSION}\nStarted: {STARTED_AT.isoformat(timespec='minutes')}")


@router.message(Command("health"))
async def health_cmd(message: Message):
    ok_worker = "unknown"
    try:
        import aiohttp, os
        url = os.getenv("RELAY_PULL_URL", "")
        secret = os.getenv("RELAY_SECRET", "")
        if url and secret:
            async with aiohttp.ClientSession() as s:
                async with s.get(url + "?chat_id=0&limit=0", headers={"X-Auth": secret}, timeout=5) as r:
                    ok_worker = f"{r.status}"
        else:
            ok_worker = "not-configured"
    except Exception as e:
        ok_worker = f"error: {e}"
    await message.reply(
        "Health:\n"
        f"• Worker /pull: {ok_worker}\n"
        f"• Pull interval: {os.getenv('RELAY_PULL_INTERVAL_S', '15')}s\n"
        f"• Families: {len(families.list())}\n"
        "• Logs: derived-only JSONL"
    )


# ========== IMPORTS ==========
import asyncio
import json
import os
from datetime import datetime
from typing import Optional, List
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from loguru import logger

from .models import EventRecord, FeatureSummary, PwaSessionReport
from .storage import Storage
from .analysis_audio import process_voice_note
from .wt_utils import (
    mint_autoingest_token,
    build_pwa_deeplink,
    redact_url_token,
    get_env,
)
from .families import FamiliesStore
from .reason_client import create_reasoner_config, ReasonClient, ReasonerUnavailable, clamp_metric_overrides, truncate_tips
from .dyad_registry import dyad_registry
from .utils import convert_pwa_to_bot_format, extract_dyad_label
from .profiles import profiles
from .analysis_image import analyze_photo, get_lighting_tip
from .analysis_video import analyze_video, get_motion_tip
from .cards import render_summary_card

APP_VERSION = "v0.2.0-beta"
STARTED_AT = datetime.now()

# Concurrency control for voice processing
VOICE_SEM = asyncio.Semaphore(2)

# Simple in-memory tracker for last voice session
LAST_SESSION = {}

# Store message IDs for voice messages to enable replies
VOICE_MESSAGE_IDS = {}

# ========== STORAGE INSTANCE ==========
storage = Storage()

# ========== CONSTANTS ==========
PWA_HOST = os.getenv("PWA_HOST", "purplewarren.github.io")

# ========== ROUTER ==========
router = Router()

# ========== HELPER FUNCTIONS ==========
async def check_onboarding_complete(message: Message) -> bool:
    """Check if user has completed onboarding."""
    try:
        family_id = f"fam_{message.chat.id}"
        profile = await profiles.get_profile_by_chat(message.chat.id)
        
        if not profile or not profile.get("complete", False):
            await message.reply(
                "🔐 Please complete onboarding first. Type /start to begin."
            )
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking onboarding status: {e}")
        await message.reply("Error checking status. Please try /start again.")
        return False

# ========== COMMAND HANDLERS ==========
@router.message(Command("summon_helper"))
async def summon_helper_command(message: Message):
    """Handle /summon_helper command - show Dyad selection."""
    if not await check_onboarding_complete(message):
        return
        
    try:
        family_id = f"fam_{message.chat.id}"
        locale = get_locale(message.chat.id)
        
        # Show available Dyads
        dyads_text = "Choose your helper:\n\n"
        dyads = dyad_registry.get_all_dyads()
        
        for dyad_id, dyad in dyads.items():
            icon = dyad.get("icon", "🔧")
            name = dyad.get("name", dyad_id)
            purpose = dyad.get("purpose", "")
            dyads_text += f"{icon} **{name}**\n{purpose}\n\n"
        
        # Create keyboard with all Dyads
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{dyad.get('icon', '🔧')} {dyad.get('name', dyad_id)}", 
                                callback_data=f"dyad_invoke:{dyad_id}")]
            for dyad_id, dyad in dyads.items()
        ])
        
        await message.reply(dyads_text, reply_markup=kb, parse_mode="Markdown")
        
        # Log Dyad selection event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_dyad_selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="dyad_selection",
            actor="parent",
            event="dyad_selection_shown",
            labels=["dyad_selection"]
        )
        storage.append_event(event)
        
        logger.info(f"Dyad selection shown for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in summon helper command: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")

@router.callback_query(F.data.startswith("dyad_invoke:"))
async def handle_dyad_invocation(callback: CallbackQuery):
    """Handle Dyad invocation - show ritualized introduction."""
    try:
        dyad_id = callback.data.split(":", 1)[1]
        family_id = f"fam_{callback.message.chat.id}"
        locale = get_locale(callback.message.chat.id)
        
        # Get Dyad metadata
        dyad = dyad_registry.get_dyad(dyad_id)
        if not dyad:
            await callback.answer("Dyad not found", show_alert=True)
            return
        
        # Get invocation text in user's locale
        invocation_text = dyad_registry.get_dyad_text(dyad_id, "invocation_text", locale)
        
        # Create invocation keyboard
        kb = create_dyad_invocation_kb(dyad_id, locale)
        
        await callback.message.edit_text(
            invocation_text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
        
        # Log Dyad invocation event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_dyad_invoked_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="dyad_invocation",
            actor="parent",
            event="dyad_invoked",
            labels=[dyad_id, "invoked"]
        )
        storage.append_event(event)
        
        logger.info(f"Dyad invoked: {dyad_id} for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in Dyad invocation: {e}")
        await callback.answer("Error occurred", show_alert=True)

@router.callback_query(F.data.startswith("dyad_launch:"))
async def handle_dyad_launch(callback: CallbackQuery):
    """Handle Dyad launch - generate PWA URL and launch."""
    try:
        dyad_id = callback.data.split(":", 1)[1]
        family_id = f"fam_{callback.message.chat.id}"
        
        # Get Dyad metadata
        dyad = dyad_registry.get_dyad(dyad_id)
        if not dyad:
            await callback.answer("Dyad not found", show_alert=True)
            return
        
        # Create Dyad URL
        dyad_url = dyad_registry.create_dyad_url(family_id, dyad_id, "en")
        
        # Get launch text
        launch_text = dyad_registry.get_dyad_text(dyad_id, "launch_cta", "en")
        
        # Create launch message
        launch_message = (
            f"{dyad.get('icon', '🔧')} **{dyad.get('name', dyad_id)}**\n\n"
            f"{dyad.get('purpose', '')}\n\n"
            f"🔗 [{launch_text}]({dyad_url})\n\n"
            f"*{dyad_registry.get_dyad_text(dyad_id, 'privacy_text', 'en')}*"
        )
        
        await callback.message.edit_text(
            launch_message,
            parse_mode="Markdown"
        )
        
        # Log Dyad launch
        session_id = f"{family_id}_{dyad_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dyad_registry.log_dyad_launch(family_id, dyad_id, session_id)
        
        logger.info(f"Dyad launched: {dyad_id} for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in Dyad launch: {e}")
        await callback.answer("Error occurred", show_alert=True)

@router.callback_query(F.data.startswith("dyad_info:"))
async def handle_dyad_info(callback: CallbackQuery):
    """Handle Dyad info - show detailed information."""
    try:
        dyad_id = callback.data.split(":", 1)[1]
        family_id = f"fam_{callback.message.chat.id}"
        
        # Get Dyad metadata
        dyad = dyad_registry.get_dyad(dyad_id)
        if not dyad:
            await callback.answer("Dyad not found", show_alert=True)
            return
        
        # Create info message
        info_message = (
            f"{dyad.get('icon', '🔧')} **{dyad.get('name', dyad_id)}**\n\n"
            f"**Purpose:** {dyad.get('purpose', '')}\n"
            f"**Tone:** {dyad.get('tone', '')}\n\n"
            f"**Privacy:** {dyad_registry.get_dyad_text(dyad_id, 'privacy_text', 'en')}\n\n"
            f"*This Dyad processes only derived signals from your device. No raw audio is ever uploaded.*"
        )
        
        # Create back button
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Back to Launch", callback_data=f"dyad_invoke:{dyad_id}")]
        ])
        
        await callback.message.edit_text(
            info_message,
            reply_markup=kb,
            parse_mode="Markdown"
        )
        
        # Log Dyad info view
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_dyad_info_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="dyad_info",
            actor="parent",
            event="dyad_info_viewed",
            labels=[dyad_id, "info_viewed"]
        )
        storage.append_event(event)
        
        logger.info(f"Dyad info viewed: {dyad_id} for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in Dyad info: {e}")
        await callback.answer("Error occurred", show_alert=True)

# ========== DYAD-SPECIFIC COMMANDS ==========
@router.message(Command("summon_night_helper"))
async def summon_night_helper_command(message: Message):
    """Handle /summon_night_helper command - direct night helper invocation."""
    if not await check_onboarding_complete(message):
        return
    
    try:
        family_id = f"fam_{message.chat.id}"
        dyad_id = "night_helper"
        locale = get_locale(message.chat.id)
        
        # Get invocation text in user's locale
        invocation_text = dyad_registry.get_dyad_text(dyad_id, "invocation_text", locale)
        
        # Create invocation keyboard
        kb = create_dyad_invocation_kb(dyad_id, locale)
        
        await message.reply(
            invocation_text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
        
        # Log direct invocation
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_direct_invocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="dyad_invocation",
            actor="parent",
            event="direct_dyad_invoked",
            labels=[dyad_id, "direct_invoked"]
        )
        storage.append_event(event)
        
        logger.info(f"Direct Dyad invocation: {dyad_id} for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in direct Dyad invocation: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")

@router.message(Command("summon_meal_mood"))
async def summon_meal_mood_command(message: Message):
    """Handle /summon_meal_mood command - direct meal mood invocation."""
    if not await check_onboarding_complete(message):
        return
    
    try:
        family_id = f"fam_{message.chat.id}"
        dyad_id = "meal_mood"
        locale = get_locale(message.chat.id)
        
        # Get invocation text in user's locale
        invocation_text = dyad_registry.get_dyad_text(dyad_id, "invocation_text", locale)
        
        # Create invocation keyboard
        kb = create_dyad_invocation_kb(dyad_id, locale)
        
        await message.reply(
            invocation_text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
        
        # Log direct invocation
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_direct_invocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="dyad_invocation",
            actor="parent",
            event="direct_dyad_invoked",
            labels=[dyad_id, "direct_invoked"]
        )
        storage.append_event(event)
        
        logger.info(f"Direct Dyad invocation: {dyad_id} for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in direct Dyad invocation: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")

@router.message(Command("summon_tantrum_translator"))
async def summon_tantrum_translator_command(message: Message):
    """Handle /summon_tantrum_translator command - direct tantrum translator invocation."""
    if not await check_onboarding_complete(message):
        return
    
    try:
        family_id = f"fam_{message.chat.id}"
        dyad_id = "tantrum_translator"
        locale = get_locale(message.chat.id)
        
        # Get invocation text in user's locale
        invocation_text = dyad_registry.get_dyad_text(dyad_id, "invocation_text", locale)
        
        # Create invocation keyboard
        kb = create_dyad_invocation_kb(dyad_id, locale)
        
        await message.reply(
            invocation_text,
            reply_markup=kb,
            parse_mode="Markdown"
        )
        
        # Log direct invocation
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_direct_invocation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="dyad_invocation",
            actor="parent",
            event="direct_dyad_invoked",
            labels=[dyad_id, "direct_invoked"]
        )
        storage.append_event(event)
        
        logger.info(f"Direct Dyad invocation: {dyad_id} for {family_id}")
        
    except Exception as e:
        logger.error(f"Error in direct Dyad invocation: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")


@router.message(Command("analyze"))
async def analyze_command(message: Message):
    """Handle /analyze command - quick voice analysis."""
    if not await check_onboarding_complete(message):
        return
        
    try:
        family_id = f"fam_{message.chat.id}"
        
        analyze_text = (
            "🎤 **Quick Voice Analysis**\n\n"
            "Send me a voice note and I'll analyze it for you.\n\n"
            "I can help with:\n"
            "• Tantrum triggers and patterns\n"
            "• Sleep environment assessment\n"
            "• Meal time stress indicators\n\n"
            "Just record and send!"
        )
        
        await message.reply(analyze_text)
        
        # Log analyze command event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_analyze_command_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            phase="analysis",
            actor="parent",
            event="analyze_command",
            labels=["voice_analysis"]
        )
        storage.append_event(event)
        
        logger.info(f"Analyze command requested for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in analyze command: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")


@router.message(Command("privacy_offline"))
async def privacy_offline_command(message: Message):
    """Handle /privacy_offline command."""
    try:
        family_id = f"fam_{message.chat.id}"
        
        await message.reply("Acknowledged: Bot will not send proactive messages. We only reply to direct inputs.")
        
        # Log privacy event
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=f"{family_id}_privacy_{datetime.now().strftime('%Y%m%d_%H%M')}",
            phase="adhoc",
            actor="parent",
            event="privacy_offline",
            labels=["privacy_acknowledged"]
        )
        storage.append_event(event)
        
        logger.info(f"Privacy offline acknowledged for family {family_id}")
        
    except Exception as e:
        logger.error(f"Error in privacy_offline command: {e}")
        await message.reply("Sorry, something went wrong. Please try again.")


@router.message(Command("export"))
async def export_command(message: Message):
    """Handle /export command - send event log."""
    try:
        events_path = storage.get_events_file_path()
        sessions_path = storage.get_sessions_file_path()
        
        # Send events file if it exists
        if events_path.exists():
            with open(events_path, 'rb') as f:
                await message.reply_document(f, caption="Your derived event log (events.jsonl)")
        else:
            await message.reply("No events logged yet.")
        
        # Send sessions file if it exists
        if sessions_path.exists():
            with open(sessions_path, 'rb') as f:
                await message.reply_document(f, caption="Your session data (sessions.csv)")
        
        logger.info(f"Export requested for family {f'fam_{message.chat.id}'}")
        
    except Exception as e:
        logger.error(f"Error in export command: {e}")
        await message.reply("Sorry, something went wrong with the export.")


@router.message(F.voice)
async def handle_voice(message: Message):
    """Handle voice note messages."""
    try:
        family_id = f"fam_{message.chat.id}"
        session_id = f"{family_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Process voice note using new pipeline with concurrency control
        from .analysis_audio import process_voice_note
        async with VOICE_SEM:
            result, card_path = await process_voice_note(
                message.bot, message.voice.file_id, family_id, session_id
            )
        
        # Store message ID for later replies
        VOICE_MESSAGE_IDS[session_id] = message.message_id
        
        # Track last session for tagging
        LAST_SESSION[family_id] = session_id
        
        # Call reasoner for night dyad if enabled
        cfg = create_reasoner_config()
        rsp = None
        if await is_reasoner_effectively_enabled(family_id) and cfg.base_url:
            try:
                # Build reasoning request for night dyad
                req = {
                    "dyad": "night",
                    "features": sanitize_for_reasoner(result['features'] or {}),
                    "context": {},  # Empty context for voice analysis
                    "metrics": {},  # Empty metrics for voice analysis
                    "history": summarize_last_events(family_id, limit=3)  # Last 3 events for voice
                }
                
                async with ReasonClient(cfg.base_url, cfg.timeout_s) as rc:
                    t0 = time.monotonic()
                    rsp = await rc.infer(req)
                    dt_ms = int((time.monotonic() - t0) * 1000)
                    
                    # Extract cache status and tips count
                    cache_status = rsp.get("cache_status", "MISS")
                    tips_count = len(rsp.get("tips", []))
                    
                    logger.info(f"reasoner_call dyad=night cache={cache_status} latency_ms={dt_ms} tips={tips_count}")
            except ReasonerUnavailable:
                logger.warning("reasoner_call dyad=night cache=N/A latency_ms=0 tips=0 (unavailable)")
        else:
            logger.info("reasoner_call dyad=night cache=N/A latency_ms=0 tips=0 (disabled)")
        
        # Enhanced reply text with context awareness
        if any(badge in result['badges'] for badge in ['Speech', 'Fluctuating', 'High_Energy']):
            # Likely tantrum/meltdown context
            reply_text = (
                "😔 It sounds intense. You stayed with it — that matters.\n\n"
                "Choose a helper below to continue."
            )
        else:
            # Standard wind-down context
            reply_text = (
                f"Wind-Down Score: {result['score']}/100\n"
                f"Badges: {', '.join(result['badges']) if result['badges'] else '—'}\n"
                f"Tip: {result['tips'][0] if result['tips'] else '—'}\n"
                f"Privacy: All processing is local."
            )
        
        # Add reasoner tip if available
        if rsp and rsp.get("tips"):
            # Truncate tips to 25 words maximum
            tips = rsp.get("tips", [])
            truncated_tips = truncate_tips(tips, max_words=25)
            
            if truncated_tips:
                tip = truncated_tips[0]  # Take first tip only
                reply_text += f"\n\n💡 Suggested next step: {tip}"
        
        from aiogram.types import FSInputFile
        photo = FSInputFile(card_path)
        await message.reply_photo(photo, caption=reply_text, reply_markup=_dyad_kb())
        
        # Log voice analyzed event with dyad label
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=session_id,
            phase="adhoc",
            actor="parent",
            event="voice_analyzed",
            labels=result['badges'] + ["dyad:night"],  # Default to night dyad for voice analysis
            features=result['features'],
            score=result['score'],
            suggestion_id="wind_down_v1"
        )
        storage.append_event(event)
        
        logger.info(f"Voice analyzed for family {family_id}, score={result['score']}")
        
    except Exception as e:
        logger.error(f"Error processing voice note: {e}")
        await message.reply("Sorry, I couldn't analyze your voice note. Please try again.")


@router.message(F.photo)
async def handle_photo(message: Message):
    """Handle photo messages (stub implementation)."""
    try:
        family_id = f"fam_{message.chat.id}"
        session_id = f"{family_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Download photo (stub - would need actual implementation)
        # For now, just acknowledge
        await message.reply("📸 Photo analysis coming soon! For now, try sending a voice note with /analyze.")
        
        # Log photo event (stub)
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=session_id,
            phase="adhoc",
            actor="parent",
            event="photo_analyzed",
            labels=["stub_implementation"]
        )
        storage.append_event(event)
        
        logger.info(f"Photo received for family {family_id} (stub)")
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.reply("Sorry, I couldn't process your photo. Please try again.")


@router.message(F.video)
async def handle_video(message: Message):
    """Handle video messages (stub implementation)."""
    try:
        family_id = f"fam_{message.chat.id}"
        session_id = f"{family_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Download video (stub - would need actual implementation)
        # For now, just acknowledge
        await message.reply("🎥 Video analysis coming soon! For now, try sending a voice note with /analyze.")
        
        # Log video event (stub)
        event = EventRecord(
            ts=datetime.now(),
            family_id=family_id,
            session_id=session_id,
            phase="adhoc",
            actor="parent",
            event="video_analyzed",
            labels=["stub_implementation"]
        )
        storage.append_event(event)
        
        logger.info(f"Video received for family {family_id} (stub)")
        
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        await message.reply("Sorry, I couldn't process your video. Please try again.")


def classify_trigger(text: str) -> str:
    """Classify text input to determine which Dyad to offer."""
    t = text.lower()
    night = any(p in t for p in ["won't sleep","cant sleep","wind","bedtime","too loud","sleep help"])
    tantrum = any(p in t for p in ["meltdown","tantrum","screaming","crying hard","he's screaming","she's screaming"])
    meal = any(p in t for p in ["dinner","won't eat","meal","feeding","she won't eat","picky"])
    if night: return "night"
    if tantrum: return "tantrum"
    if meal: return "meal"
    return ""


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    """Handle text messages for natural language Dyad triggers."""
    try:
        family_id = f"fam_{message.chat.id}"
        text = message.text.lower().strip()
        
        logger.info(f"Received text message: '{text}' from family {family_id}")
        
        # Classify trigger
        dyad = classify_trigger(text)
        if dyad and dyad in ["night", "tantrum", "meal"]:
            await message.reply(
                "Got it. Open a helper:",
                reply_markup=_dyad_kb()
            )
            
            # Log dyad trigger
            event = EventRecord(
                ts=datetime.now(),
                family_id=family_id,
                session_id=f"{family_id}_{dyad}_trigger_{datetime.now().strftime('%Y%m%d_%H%M')}",
                phase="dyad_trigger",
                actor="parent",
                event=f"{dyad}_triggered",
                labels=[f"dyad:{dyad}", "natural_language"]
            )
            storage.append_event(event)
            return
            
        # Unrecognized input - Silli's learning response
        await message.reply(
            "I'm still learning. That moment matters, but I don't yet know how to help with it.\n\n"
            "For now, I can support sleep, tantrums, and meals.\n\n"
            "Try:\n"
            "• /night_helper - for bedtime challenges\n"
            "• /tantrum_translator - for meltdowns\n"
            "• /meal_mood - for feeding struggles"
        )
            
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        await message.reply("Sorry, something went wrong. Please try again.") 

# /ingest command handler
@router.message(Command("ingest"))
async def ingest_cmd(message: Message):
    await message.reply(
        "Send the PWA session JSON file exported from the Dyad.\n"
        "I’ll validate it, append a derived-only log event, and return a summary."
    )

# Handler for uploaded PWA session JSON document
@router.message(lambda m: m.document)
async def handle_document(message: Message):
    """Handle all document messages for debugging."""
    try:
        logger.info(f"=== DOCUMENT RECEIVED ===")
        logger.info(f"Document: {message.document.file_name}")
        logger.info(f"Type: {message.document.mime_type}")
        logger.info(f"File ID: {message.document.file_id}")
        logger.info(f"File Size: {message.document.file_size}")
        logger.info(f"Chat ID: {message.chat.id}")
        logger.info(f"From User: {message.from_user.username if message.from_user else 'Unknown'}")
        logger.info(f"Message ID: {message.message_id}")
        logger.info(f"Date: {message.date}")
        logger.info(f"========================")
        
        # Check if it's a JSON file
        if message.document.file_name and message.document.file_name.lower().endswith('.json'):
            logger.info(f"Processing JSON document: {message.document.file_name}")
            await ingest_json_handler(message)
        else:
            logger.info(f"Document {message.document.file_name} is not a JSON file")
            
    except Exception as e:
        logger.error(f"Error handling document: {e}")

async def ingest_json_handler(message: Message):
    try:
        logger.info(f"Processing JSON document: {message.document.file_name}")
        doc = message.document
        file = await message.bot.get_file(doc.file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tf:
            await message.bot.download_file(file.file_path, tf.name)
            temp_path = tf.name
        with open(temp_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        
        logger.info(f"Loaded JSON payload with keys: {list(payload.keys())}")
        
        # Convert PWA format to bot format if needed
        converted_payload = convert_pwa_to_bot_format(payload)
        logger.info(f"Converted payload with session_id: {converted_payload.get('session_id')}")
        report = PwaSessionReport(**converted_payload)
        
        # Prefer long score, fallback to mid/short
        long_score = None
        if isinstance(report.score, dict):
            long_score = report.score.get("long") or report.score.get("mid") or report.score.get("short")
        
        logger.info(f"Creating ingest_session_report event for session: {report.session_id}")
        
        # Extract dyad from payload
        dyad = payload.get('dyad') or (payload.get('config', {}) or {}).get('dyad') or 'night'
        
        # Append derived-only event with dyad label
        context = payload.get("context") or None
        metrics = payload.get("metrics") or None
        event = EventRecord(
            ts=datetime.now(),
            family_id=report.family_id,
            session_id=report.session_id,
            phase=report.mode,
            actor="parent",
            event="ingest_session_report",
            labels=(report.badges or []) + [f"dyad:{dyad}"],
            features=report.features_summary,
            score=int(long_score) if isinstance(long_score, (int, float)) else None,
            context=context,
            metrics=metrics,
            suggestion_id=None
        )
        storage.append_event(event)
        logger.info(f"Successfully created ingest_session_report event for session: {report.session_id}")
        
        # Build reasoning request
        req = {
            "dyad": dyad,
            "features": sanitize_for_reasoner(report.features_summary or {}),
            "context": redact_pii_context(payload.get("context") or {}),
            "metrics": sanitize_for_reasoner(payload.get("metrics") or {}),
            "history": summarize_last_events(report.family_id, limit=5)
        }
        
        # Call reasoner if enabled
        cfg = create_reasoner_config()
        rsp = None
        cache_status = "N/A"
        if await is_reasoner_effectively_enabled(report.family_id) and cfg.base_url:
            try:
                async with ReasonClient(cfg.base_url, cfg.timeout_s) as rc:
                    t0 = time.monotonic()
                    rsp = await rc.infer(req)
                    dt_ms = int((time.monotonic() - t0) * 1000)
                    
                    # Extract cache status and tips count
                    cache_status = rsp.get("cache_status", "MISS")
                    tips_count = len(rsp.get("tips", []))
                    
                    logger.info(f"reasoner_call dyad={dyad} cache={cache_status} latency_ms={dt_ms} tips={tips_count}")
            except ReasonerUnavailable:
                logger.warning("reasoner_call dyad={dyad} cache=N/A latency_ms=0 tips=0 (unavailable)")
        else:
            logger.info("reasoner_call dyad={dyad} cache=N/A latency_ms=0 tips=0 (disabled)")
        
        # Merge reasoner results into event
        if rsp and rsp.get("metric_overrides"):
            overrides = rsp["metric_overrides"]
            if not event.metrics:
                event.metrics = {}
            
            # Apply metric overrides with strict clamping
            clamped_overrides = clamp_metric_overrides(overrides)
            event.metrics.update(clamped_overrides)
            
            # Log which metric overrides were applied
            applied_metrics = list(clamped_overrides.keys())
            if applied_metrics:
                logger.info(f"reasoner_merge dyad={dyad} metrics={','.join(applied_metrics)}")
        
        # Store reasoning context with truncated tips
        if not event.context:
            event.context = {}
        
        # Truncate tips to 25 words maximum
        tips = rsp.get("tips", []) if rsp else []
        truncated_tips = truncate_tips(tips, max_words=25)
        
        event.context["reasoning"] = {
            "tips": truncated_tips[:2],  # Limit to 2 tips
            "rationale": rsp.get("rationale", "") if rsp else "",
            "model": os.getenv("REASONER_MODEL_HINT", ""),
            "ts": datetime.utcnow().isoformat()
        }
        
        # Update the event in storage with reasoning data
        storage.append_event(event)
        
        # Prepare summary with dyad-specific metrics
        trend = report.score.get("trend") if isinstance(report.score, dict) else None
        summary_text = (
            "Session ingested ✅\n"
            f"• Session: {report.session_id}\n"
            f"• Duration: {int(report.duration_s)}s\n"
            f"• Score (long): {long_score}\n"
            f"• Trend: {trend or '—'}\n"
            f"• Badges: {', '.join(report.badges) if report.badges else '—'}"
        )
        
        # Add dyad-specific metrics
        if "dyad:tantrum" in event.labels and event.metrics and event.metrics.get("escalation_index") is not None:
            escalation = event.metrics["escalation_index"]
            summary_text += f"\n• Escalation Index: {escalation:.2f}"
        
        if "dyad:meal" in event.labels and event.metrics and event.metrics.get("meal_mood") is not None:
            meal_mood = event.metrics["meal_mood"]
            summary_text += f"\n• Meal Mood: {int(meal_mood)}"
        
        # Add AI suggestions if available
        if event.context and event.context.get("reasoning") and event.context["reasoning"].get("tips"):
            tips = event.context["reasoning"]["tips"]
            if tips:
                summary_text += "\n\nSuggested next step:"
                for tip in tips[:2]:  # Limit to 2 tips
                    summary_text += f"\n• {tip}"
        
        await message.reply(summary_text)
    except Exception as e:
        logger.error(f"Error ingesting JSON: {e}")
        await message.reply(f"Could not ingest JSON: {e}")
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


# Tag voice handler
@router.message(F.text.startswith("/tag "))
async def tag_voice(message: Message):
    try:
        family_id = f"fam_{message.chat.id}"
        parts = message.text.split()
        if len(parts) != 2:
            return await message.reply("Usage: /tag quiet | speech | tv_music | white_noise")
        
        label = parts[1].lower()
        if label not in ["quiet", "speech", "tv_music", "white_noise"]:
            return await message.reply("Invalid tag. Use: quiet | speech | tv_music | white_noise")
        
        # Get the most recent session (voice or PWA)
        events = storage.get_events(family_id)
        voice_events = [e for e in events if e.event == "voice_analyzed"]
        pwa_events = [e for e in events if e.event == "pwa_session_complete"]
        
        if not voice_events and not pwa_events:
            return await message.reply("No recent sessions to tag. Send a voice clip or run a PWA session first.")
        
        # Get the most recent session
        all_sessions = voice_events + pwa_events
        latest_session = max(all_sessions, key=lambda e: e.ts)
        sid = latest_session.session_id
        
        storage.append_event(EventRecord(
            ts=datetime.now(), family_id=family_id, session_id=sid,
            phase="adhoc", actor="parent", event="tag_voice",
            labels=[label]
        ))
        
        logger.info(f"Tagged session {sid} as '{label}' for family {family_id}")
        await message.reply(f"Tagged session {sid} as '{label}'. Thanks!")
        
    except Exception as e:
        logger.error(f"Error tagging voice: {e}")
        await message.reply("Sorry, couldn't tag the voice. Please try again.")


# List voice notes command
@router.message(Command("list"))
async def list_voice_notes(message: Message):
    try:
        family_id = f"fam_{message.chat.id}"
        
        # Get all events for this family
        events = storage.get_events(family_id)
        
        from collections import defaultdict
        by_day = defaultdict(list)
        for e in events:
            if e.event in ["voice_analyzed", "pwa_session_complete", "ingest_session_report"]:
                day = e.ts.strftime("%Y-%m-%d")
                by_day[day].append(e)

        days = sorted(by_day.keys(), reverse=True)[:3]  # last 3 days
        lines = [f"📊 Sessions (last {len(days)} day(s))"]
        shown = 0
        for d in days:
            lines.append(f"\n📅 {d}")
            for e in sorted(by_day[d], key=lambda x: x.ts, reverse=True):
                short_id = e.session_id.split("_")[-1] if "_" in e.session_id else e.session_id[-8:]
                score = e.score if e.score is not None else "—"
                tag = "—"
                for t in reversed([x for x in events if x.event == "tag_voice" and x.session_id == e.session_id]):
                    tag = t.labels[0] if t.labels else "—"
                    break
                emoji = "🎵" if e.event == "voice_analyzed" else "📱"
                line = f"{emoji} {short_id} · score {score} · tag {tag}"
                if hasattr(e, 'labels') and e.labels:
                    for label in e.labels:
                        if label.startswith('dyad:'):
                            line += f" · {label}"
                            break
                if e.event == "ingest_session_report":
                    if 'dyad:tantrum' in e.labels and e.metrics and e.metrics.get('escalation_index'):
                        line += f" · esc={e.metrics['escalation_index']:.2f}"
                    if 'dyad:meal' in e.labels and e.metrics and e.metrics.get('meal_mood'):
                        line += f" · mood={e.metrics['meal_mood']:.0f}"
                lines.append(line)
                shown += 1
                if shown >= 5: break
            if shown >= 5: break

        await message.reply("\n".join(lines))
        
    except Exception as e:
        logger.error(f"Error listing voice notes: {e}")
        await message.reply("Sorry, couldn't list the sessions. Please try again.")


@router.message(Command("reason_stats"))
async def reason_stats_command(message: Message):
    """Show reasoner statistics from recent logs (admin only)"""
    try:
        # Read the last 50 lines of the log file
        log_file = Path("logs/silli_bot.log")
        if not log_file.exists():
            await message.reply("❌ No log file found. Bot may not have started yet.")
            return
        
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        # Get last 50 lines and filter for reasoner calls
        recent_lines = lines[-50:] if len(lines) >= 50 else lines
        reasoner_calls = []
        
        for line in recent_lines:
            if "reasoner_call" in line:
                # Parse the reasoner call log line
                # Format: reasoner_call dyad=<d> cache=<HIT|MISS> latency_ms=<x> tips=<n>
                try:
                    # Extract dyad, cache status, latency, and tips
                    parts = line.split()
                    dyad = None
                    cache_status = None
                    latency_ms = None
                    tips_count = None
                    
                    for part in parts:
                        if part.startswith("dyad="):
                            dyad = part.split("=")[1]
                        elif part.startswith("cache="):
                            cache_status = part.split("=")[1]
                        elif part.startswith("latency_ms="):
                            latency_ms = int(part.split("=")[1])
                        elif part.startswith("tips="):
                            tips_count = int(part.split("=")[1])
                    
                    if dyad and cache_status and latency_ms is not None and tips_count is not None:
                        reasoner_calls.append({
                            'dyad': dyad,
                            'cache': cache_status,
                            'latency_ms': latency_ms,
                            'tips': tips_count
                        })
                except Exception:
                    # Skip malformed lines
                    continue
        
        if not reasoner_calls:
            await message.reply("📊 No reasoner calls found in recent logs.")
            return
        
        # Calculate statistics
        total_calls = len(reasoner_calls)
        cache_hits = sum(1 for call in reasoner_calls if call['cache'] == 'HIT')
        cache_misses = sum(1 for call in reasoner_calls if call['cache'] == 'MISS')
        cache_hit_rate = (cache_hits / total_calls) * 100 if total_calls > 0 else 0
        
        avg_latency = sum(call['latency_ms'] for call in reasoner_calls) / total_calls
        min_latency = min(call['latency_ms'] for call in reasoner_calls)
        max_latency = max(call['latency_ms'] for call in reasoner_calls)
        
        # Count by dyad
        dyad_counts = {}
        for call in reasoner_calls:
            dyad = call['dyad']
            dyad_counts[dyad] = dyad_counts.get(dyad, 0) + 1
        
        # Count calls with tips
        calls_with_tips = sum(1 for call in reasoner_calls if call['tips'] > 0)
        avg_tips = sum(call['tips'] for call in reasoner_calls) / total_calls
        
        # Build report
        report_lines = []
        report_lines.append("🤖 **Reasoner Statistics (Last 50 Calls)**")
        report_lines.append("")
        report_lines.append(f"📊 **Overview:**")
        report_lines.append(f"• Total calls: {total_calls}")
        report_lines.append(f"• Cache hits: {cache_hits} ({cache_hit_rate:.1f}%)")
        report_lines.append(f"• Cache misses: {cache_misses}")
        report_lines.append("")
        report_lines.append(f"⏱️ **Performance:**")
        report_lines.append(f"• Avg latency: {avg_latency:.0f}ms")
        report_lines.append(f"• Min latency: {min_latency}ms")
        report_lines.append(f"• Max latency: {max_latency}ms")
        report_lines.append("")
        report_lines.append(f"💡 **Tips:**")
        report_lines.append(f"• Calls with tips: {calls_with_tips}/{total_calls}")
        report_lines.append(f"• Avg tips per call: {avg_tips:.1f}")
        report_lines.append("")
        report_lines.append(f"🎯 **By Dyad:**")
        for dyad, count in sorted(dyad_counts.items()):
            report_lines.append(f"• {dyad}: {count} calls")
        
        await message.reply("\n".join(report_lines))
        
    except Exception as e:
        logger.error(f"Error generating reasoner stats: {e}")
        await message.reply(f"❌ Error generating statistics: {str(e)}")


@router.message(Command("families"))
async def families_cmd(message: Message):
    ids = families.list()
    if not ids:
        return await message.reply("No families registered yet.")
    await message.reply("Families:\n" + "\n".join(str(i) for i in ids))


@router.message(F.text.startswith("/families_remove "))
async def families_remove(message: Message):
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply("Usage: /families_remove <chat_id>")
    try:
        cid = int(parts[1])
        families.remove(cid)
        await message.reply(f"Removed {cid} from roster.")
    except Exception as e:
        await message.reply(f"Failed: {e}")


# Tag specific session command
@router.message(F.text.startswith("/tag_session "))
async def tag_session(message: Message):
    try:
        family_id = f"fam_{message.chat.id}"
        parts = message.text.split()
        if len(parts) != 3:
            return await message.reply("Usage: /tag_session <short_id> <tag>\nExample: /tag_session 202224 quiet")
        
        short_id = parts[1]
        label = parts[2].lower()
        
        if label not in ["quiet", "speech", "tv_music", "white_noise"]:
            return await message.reply("Invalid tag. Use: quiet | speech | tv_music | white_noise")
        
        # Get all voice analyzed and PWA session events for this family
        events = storage.get_events(family_id)
        voice_events = [e for e in events if e.event == "voice_analyzed"]
        pwa_events = [e for e in events if e.event in ["pwa_session_complete", "ingest_session_report"]]
        
        # Find the session by short_id (check both voice and PWA sessions)
        target_session = None
        for event in voice_events + pwa_events:
            session_id = event.session_id
            session_short_id = session_id.split("_")[-1] if "_" in session_id else session_id[-8:]
            if session_short_id == short_id:
                target_session = session_id
                break
        
        if not target_session:
            return await message.reply(f"Session {short_id} not found. Use `/list` to see available sessions.")
        
        storage.append_event(EventRecord(
            ts=datetime.now(), family_id=family_id, session_id=target_session,
            phase="adhoc", actor="parent", event="tag_voice",
            labels=[label]
        ))
        
        logger.info(f"Tagged session {target_session} as '{label}' for family {family_id}")
        await message.reply(f"Tagged session {short_id} as '{label}'. Thanks!")
        
    except Exception as e:
        logger.error(f"Error tagging session: {e}")
        await message.reply("Sorry, couldn't tag the session. Please try again.")


async def is_reasoner_effectively_enabled(family_id: str) -> bool:
    """
    Check if reasoner is effectively enabled for a family.
    
    Effective enablement = (Global REASONER_ENABLED == True) AND (Family cloud_reasoning == True)
    
    Args:
        family_id: The family ID to check
        
    Returns:
        True if reasoner should be used for this family, False otherwise
    """
    # Check global setting
    global_enabled = os.getenv('REASONER_ENABLED', '0').lower() in ('1', 'true', 'yes')
    if not global_enabled:
        return False
    
    # Check family setting
    try:
        profile = await profiles.get_profile(family_id)
        if not profile:
            return False
        
        return profile.cloud_reasoning
    except Exception:
        # If we can't get the profile, default to disabled
        return False