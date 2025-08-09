from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from contextlib import suppress
from typing import Optional
from loguru import logger
from .profiles import profiles
from .families import families
from .dyad_registry import dyad_registry
from .i18n import get_locale, get_localized_text, t
from .utils.text import b, h
from .config import config
from datetime import datetime
import json

router_finish_setup = Router(name="finish_setup")

def _safe_answer(q: CallbackQuery, text: Optional[str] = None):
    """Safely answer a callback query."""
    return q.answer(text=text, cache_time=2)

def _safe_edit_message(q: CallbackQuery, **kwargs):
    """Safely edit a message, ignoring 'message is not modified' errors."""
    with suppress(TelegramBadRequest):
        try:
            return q.message.edit_reply_markup(**kwargs)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise


def _pwa_url(dyad_key: str, token: str) -> str:
    """Generate PWA URL with token for dyad launch."""
    # Get PWA host and path from environment
    import os
    pwa_host = os.getenv("PWA_HOST", "localhost:5173").rstrip("/")
    pwa_path = os.getenv("PWA_PATH", "").strip("/")
    
    # Map registry dyad IDs to PWA-compatible IDs
    dyad_mapping = {
        "night_helper": "night",
        "meal_mood": "meal",
        "tantrum_translator": "tantrum"
    }
    pwa_dyad = dyad_mapping.get(dyad_key, dyad_key)
    
    # Build the full URL
    if pwa_path:
        return f"https://{pwa_host}/{pwa_path}/?dyad={pwa_dyad}&token={token}"
    else:
        return f"https://{pwa_host}/?dyad={pwa_dyad}&token={token}"


def create_finish_setup_keyboard(locale: str, family_data: dict) -> InlineKeyboardMarkup:
    """Create the finish setup keyboard with current state."""
    enabled_dyads = set(family_data.get("enabled_dyads", []))
    cloud_reasoning = family_data.get("cloud_reasoning", False)
    
    enable_text = t(locale, "btn_enable")
    disable_text = t(locale, "btn_disable")
    about_text = t(locale, "btn_about")
    
    if locale == "pt_br":
        ai_text = "IA (20B)"
        recommended_text = " (recomendado)"
    else:
        ai_text = "AI (20B)"
        recommended_text = " (recommended)"
    
    keyboard = []
    
    # Dyad buttons
    for dyad_key in ["night_helper", "tantrum_translator", "meal_mood"]:
        dyad_info = dyad_registry.get_dyad(dyad_key)
        if not dyad_info:
            continue
            
        dyad_name = dyad_info.get("name", dyad_key.title())
        icon = dyad_info.get("icon", "🎯")
        
        if dyad_key in enabled_dyads:
            # Dyad is enabled - show disable option
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{icon} {dyad_name} - {disable_text}",
                    callback_data=f"fs:dyad:disable:{dyad_key}"
                ),
                InlineKeyboardButton(
                    text=about_text,
                    callback_data=f"fs:consent:show:{dyad_key}"
                )
            ])
        else:
            # Dyad is disabled - show enable option
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{icon} {dyad_name} - {enable_text}",
                    callback_data=f"fs:dyad:enable:{dyad_key}"
                ),
                InlineKeyboardButton(
                    text=about_text,
                    callback_data=f"fs:consent:show:{dyad_key}"
                )
            ])
    
    # Add debug pulse button (temporary for testing)
    keyboard.append([
        InlineKeyboardButton(
            text=t(locale, "pong"),
            callback_data="fs:pulse"
        )
    ])
    
    # AI toggle button
    if cloud_reasoning:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🤖 {ai_text} - {disable_text}",
                callback_data="fs:ai:toggle:off"
            )
        ])
    else:
        # Check if AI should be preselected
        ai_button_text = f"🤖 {ai_text} - {enable_text}"
        if config.REASONER_DEFAULT_ON:
            ai_button_text += recommended_text
        
        keyboard.append([
            InlineKeyboardButton(
                text=ai_button_text,
                callback_data="fs:ai:toggle:on"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def show_finish_setup_card(message: Message, family_id: str):
    """Show the finish setup card."""
    locale = get_locale(message.chat.id)
    
    # Get family data
    family = families.get_family(family_id)
    if not family:
        text = t(locale, "err_status")
        await message.answer(text)
        return
    
    # Convert family to dict for easier manipulation
    family_data = family.model_dump() if hasattr(family, 'model_dump') else family.__dict__
    
    header_text = b(t(locale, "finish_header"))
    consent_blurb = t(locale, "consent_blurb")
    text = f"{header_text}\n\n{consent_blurb}"
    
    keyboard = create_finish_setup_keyboard(locale, family_data)
    
    await message.answer(text, reply_markup=keyboard)
    logger.info(f"finish_setup_open family={family_id}")


# Debug handler to prove callbacks reach the router
@router_finish_setup.callback_query(F.data == "fs:pulse")
async def fs_pulse(callback: CallbackQuery):
    """Debug handler to test callback routing."""
    locale = get_locale(callback.message.chat.id)
    await _safe_answer(callback, t(locale, "pong"))
    logger.info("fs:pulse debug callback received and handled successfully")


@router_finish_setup.callback_query(F.data == "finish:open")
async def handle_finish_setup_open(callback: CallbackQuery):
    """Handle opening the finish setup card."""
    await _safe_answer(callback)
    
    # Get user's family ID
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        locale = get_locale(callback.message.chat.id)
        text = t(locale, "err_status")
        await callback.message.answer(text)
        return
    
    family_id = profile["family_id"]
    await show_finish_setup_card(callback.message, family_id)


@router_finish_setup.callback_query(F.data.startswith("fs:dyad:enable:"))
async def handle_dyad_enable(callback: CallbackQuery):
    """Handle enabling a dyad."""
    await _safe_answer(callback)
    
    dyad_key = callback.data.split(":")[3]  # fs:dyad:enable:meal_mood
    locale = get_locale(callback.message.chat.id)
    
    # Get family data
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer("❌ No family found.")
        return
    
    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer("❌ Family not found.")
        return
    
    # Check if consent is required and given
    consents = getattr(family, 'consents', {}) or {}
    dyad_consent = consents.get(dyad_key, {})
    
    if not dyad_consent.get("accepted", False):
        # Show consent modal - call the new consent handler directly
        consent_callback_data = f"fs:consent:show:{dyad_key}"
        # Create a mock callback with the right data
        mock_callback = type('obj', (), {
            'data': consent_callback_data,
            'message': callback.message
        })()
        await fs_consent_show(mock_callback)
    else:
        # Consent already given, enable directly
        await enable_dyad(callback.message, family_id, dyad_key, locale)


async def enable_dyad(message: Message, family_id: str, dyad_key: str, locale: str):
    """Enable a dyad and update the family."""
    # Get current family data
    family = families.get_family(family_id)
    if not family:
        return
    
    # Update enabled dyads
    enabled_dyads = list(getattr(family, 'enabled_dyads', []) or [])
    if dyad_key not in enabled_dyads:
        enabled_dyads.append(dyad_key)
    
    # Update family
    families.upsert_fields(family_id, enabled_dyads=enabled_dyads)
    
    # Log the action
    logger.info(f"dyad_enable dyad={dyad_key} accepted=true")
    
    # Show success message
    dyad_info = dyad_registry.get_dyad(dyad_key)
    dyad_name = dyad_info.get("name", dyad_key.title()) if dyad_info else dyad_key.title()
    
    if locale == "pt_br":
        await message.answer(f"✅ {dyad_name} ativado!")
    else:
        await message.answer(f"✅ {dyad_name} enabled!")
    
    # Refresh the finish setup card
    await show_finish_setup_card(message, family_id)


# New consent handlers per CTO's fix
@router_finish_setup.callback_query(F.data.startswith("fs:consent:show:"))
async def fs_consent_show(callback: CallbackQuery):
    """Show consent modal for a dyad."""
    await _safe_answer(callback)
    
    # Parse dyad key: fs:consent:show:meal_mood
    dyad_key = callback.data.split(":", 3)[-1]
    
    # Get family + locale
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer("❌ No family found.")
        return
    
    family = families.get_family(profile["family_id"])
    if not family:
        await callback.message.answer("❌ Family not found.")
        return
    
    locale = get_locale(callback.message.chat.id)
    
    # Fetch dyad + consent text
    dyad_info = dyad_registry.get_dyad(dyad_key)
    if not dyad_info:
        await callback.message.answer("❌ Dyad not found.")
        return
    
    raw_consent_text = dyad_info.get("consent_text", "")
    consent_text = get_localized_text(raw_consent_text, locale)
    
    if not consent_text:
        await callback.message.answer("❌ No consent information available.")
        return
    
    # Render consent with actions
    if locale == "pt_br":
        header = "Como este ajudante usa seus dados"
        accept_text = "Aceitar"
        decline_text = "Recusar"
        tip_text = "💡 Dica: Mantenha as dicas com ≤25 palavras para melhor experiência."
    else:
        header = "How this helper uses your data"
        accept_text = "Accept"
        decline_text = "Decline"
        tip_text = "💡 Tip: Keep tips ≤25 words for best experience."
    
    consent_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=accept_text,
                callback_data=f"fs:consent:accept:{dyad_key}"
            ),
            InlineKeyboardButton(
                text=decline_text,
                callback_data=f"fs:consent:decline:{dyad_key}"
            )
        ]
    ])
    
    await callback.message.answer(
        f"**{header}**\n\n{consent_text}\n\n{tip_text}",
        reply_markup=consent_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router_finish_setup.callback_query(F.data.startswith("fs:consent:accept:"))
async def fs_consent_accept(callback: CallbackQuery):
    """Accept consent and enable dyad."""
    await _safe_answer(callback, text="Enabled")
    
    # Parse dyad key: fs:consent:accept:meal_mood
    dyad_key = callback.data.split(":", 3)[-1]
    
    # Get family
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer("❌ No family found.")
        return
    
    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer("❌ Family not found.")
        return
    
    # Persist consent + enable dyad
    consents = getattr(family, 'consents', {}) or {}
    consents[dyad_key] = {
        "accepted": True,
        "ts": datetime.now().isoformat()
    }
    
    enabled_dyads = list(getattr(family, 'enabled_dyads', []) or [])
    if dyad_key not in enabled_dyads:
        enabled_dyads.append(dyad_key)
    
    families.upsert_fields(family_id, consents=consents, enabled_dyads=enabled_dyads)
    
    logger.info(f"dyad_enable dyad={dyad_key} family={family_id} accepted=1")
    
    # Show success and re-render finish-setup card
    locale = get_locale(callback.message.chat.id)
    dyad_info = dyad_registry.get_dyad(dyad_key)
    dyad_name = dyad_info.get("name", dyad_key.title()) if dyad_info else dyad_key.title()
    
    if locale == "pt_br":
        await callback.message.answer(f"✅ {dyad_name} ativado!")
    else:
        await callback.message.answer(f"✅ {dyad_name} enabled!")
    
    await show_finish_setup_card(callback.message, family_id)


@router_finish_setup.callback_query(F.data.startswith("fs:consent:decline:"))
async def fs_consent_decline(callback: CallbackQuery):
    """Decline consent."""
    await _safe_answer(callback, text="Declined")
    
    # Parse dyad key: fs:consent:decline:meal_mood
    dyad_key = callback.data.split(":", 3)[-1]
    
    # Get family
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer("❌ No family found.")
        return
    
    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer("❌ Family not found.")
        return
    
    # Persist consent decline
    consents = getattr(family, 'consents', {}) or {}
    consents[dyad_key] = {
        "accepted": False,
        "ts": datetime.now().isoformat()
    }
    
    families.upsert_fields(family_id, consents=consents)
    
    logger.info(f"dyad_enable dyad={dyad_key} family={family_id} accepted=0")
    
    locale = get_locale(callback.message.chat.id)
    if locale == "pt_br":
        await callback.message.answer("❌ Consentimento recusado. Dyad não ativado.")
    else:
        await callback.message.answer("❌ Consent declined. Dyad not enabled.")
    
    await show_finish_setup_card(callback.message, family_id)


@router_finish_setup.callback_query(F.data.startswith("fs:ai:consent:"))
async def handle_ai_consent(callback: CallbackQuery):
    """Handle AI consent responses."""
    await _safe_answer(callback)
    
    action = callback.data.split(":")[3]  # fs:ai:consent:accept
    locale = get_locale(callback.message.chat.id)
    
    # Get family data
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer("❌ No family found.")
        return
    
    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer("❌ Family not found.")
        return
    
    # Get current consents
    consents = getattr(family, 'consents', {}) or {}
    
    if action == "accept":
        # Update consent
        consents["ai_20b"] = {
            "accepted": True,
            "ts": datetime.now().isoformat()
        }
        
        # Update family
        families.upsert_fields(family_id, consents=consents)
        
        # Log the action
        logger.info(f"reasoner_opt_in family={family_id} user={callback.message.chat.id} source=finish_setup value=yes")
        
        # Enable AI
        await enable_ai(callback.message, family_id, locale)
        
    elif action == "decline":
        # Update consent
        consents["ai_20b"] = {
            "accepted": False,
            "ts": datetime.now().isoformat()
        }
        
        # Update family
        families.upsert_fields(family_id, consents=consents)
        
        # Log the action
        logger.info(f"reasoner_opt_in family={family_id} user={callback.message.chat.id} source=finish_setup value=no")
        
        if locale == "pt_br":
            await callback.message.answer("❌ Consentimento recusado. IA não ativada.")
        else:
            await callback.message.answer("❌ Consent declined. AI not enabled.")
        
        # Refresh the finish setup card
        await show_finish_setup_card(callback.message, family_id)


@router_finish_setup.callback_query(F.data.startswith("fs:dyad:disable:"))
async def handle_dyad_disable(callback: CallbackQuery):
    """Handle disabling a dyad."""
    await _safe_answer(callback)
    
    dyad_key = callback.data.split(":")[3]  # fs:dyad:disable:meal_mood
    locale = get_locale(callback.message.chat.id)
    
    # Get family data
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer("❌ No family found.")
        return
    
    family_id = profile["family_id"]
    
    # Get current family data
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer("❌ Family not found.")
        return
    
    # Update enabled dyads
    enabled_dyads = list(getattr(family, 'enabled_dyads', []) or [])
    if dyad_key in enabled_dyads:
        enabled_dyads.remove(dyad_key)
    
    # Update family
    families.upsert_fields(family_id, enabled_dyads=enabled_dyads)
    
    # Show success message
    dyad_info = dyad_registry.get_dyad(dyad_key)
    dyad_name = dyad_info.get("name", dyad_key.title()) if dyad_info else dyad_key.title()
    
    if locale == "pt_br":
        await callback.message.answer(f"❌ {dyad_name} desativado.")
    else:
        await callback.message.answer(f"❌ {dyad_name} disabled.")
    
    # Refresh the finish setup card
    await show_finish_setup_card(callback.message, family_id)


@router_finish_setup.callback_query(F.data.startswith("fs:ai:toggle:"))
async def handle_ai_toggle(callback: CallbackQuery):
    """Handle AI toggle."""
    await _safe_answer(callback)
    
    action = callback.data.split(":")[3]  # fs:ai:toggle:on
    locale = get_locale(callback.message.chat.id)
    
    # Get family data
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer("❌ No family found.")
        return
    
    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer("❌ Family not found.")
        return
    
    if action == "on":
        # Check if consent is required and given
        consents = getattr(family, 'consents', {}) or {}
        ai_consent = consents.get("ai_20b", {})
        
        if not ai_consent.get("accepted", False):
            # Show AI consent modal
            if locale == "pt_br":
                header = "Como a IA usa seus dados"
                consent_text = "A IA roda em nosso servidor seguro usando o modelo 20B. Resposta ~15–20s. Você pode desativar a qualquer momento com /reasoning."
                short_text = "Processa dados derivados em nosso servidor para sugerir dicas. Nenhuma mídia bruta armazenada. Você pode desativar a qualquer momento."
                accept_text = "Aceitar"
                decline_text = "Agora não"
            else:
                header = "How AI uses your data"
                consent_text = "AI runs on our secure server using a large 20B model. Typical reply ~15–20s. You can turn it off anytime with /reasoning."
                short_text = "Processes derived data on our server to suggest tips. No raw media stored. You can disable anytime."
                accept_text = "Accept"
                decline_text = "Not now"
            
            # Add privacy reminder
            if locale == "pt_br":
                reminder = "\n\n💡 Dica: Mantenha as dicas com ≤25 palavras para melhor experiência."
            else:
                reminder = "\n\n💡 Tip: Keep tips ≤25 words for best experience."
            
            consent_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=accept_text,
                        callback_data="fs:ai:consent:accept"
                    ),
                    InlineKeyboardButton(
                        text=decline_text,
                        callback_data="fs:ai:consent:decline"
                    )
                ]
            ])
            
            await callback.message.answer(
                f"**{header}**\n\n{short_text}{reminder}",
                reply_markup=consent_keyboard
            )
        else:
            # Consent already given, enable directly
            await enable_ai(callback.message, family_id, locale)
    else:
        # Disable AI
        await disable_ai(callback.message, family_id, locale)


async def enable_ai(message: Message, family_id: str, locale: str):
    """Enable AI and update the family."""
    # Get current family data
    family = families.get_family(family_id)
    if not family:
        return
    
    # Update AI setting and consent
    consents = getattr(family, 'consents', {}) or {}
    consents["ai_20b"] = {
        "accepted": True,
        "ts": datetime.now().isoformat()
    }
    
    families.upsert_fields(family_id, cloud_reasoning=True, consents=consents)
    
    # Log the action
    logger.info(f"reasoner_opt_in family={family_id} user={message.chat.id} source=finish_setup value=yes")
    
    # Show success message
    if locale == "pt_br":
        await message.answer("🤖 IA ativada! Agora você pode usar recursos de IA.")
    else:
        await message.answer("🤖 AI enabled! You can now use AI-powered features.")
    
    # Refresh the finish setup card
    await show_finish_setup_card(message, family_id)


async def disable_ai(message: Message, family_id: str, locale: str):
    """Disable AI and update the family."""
    # Get current family data
    family = families.get_family(family_id)
    if not family:
        return
    
    # Update AI setting
    families.upsert_fields(family_id, cloud_reasoning=False)
    
    # Log the action
    logger.info(f"reasoner_toggle family={family_id} user={message.chat.id} value=off")
    
    # Show success message
    if locale == "pt_br":
        await message.answer("🤖 IA desativada. Use /reasoning para reativar.")
    else:
        await message.answer("🤖 AI disabled. Use /reasoning to re-enable.")
    
    # Refresh the finish setup card
    await show_finish_setup_card(message, family_id)


# ========== NEW DYAD LAUNCH HANDLERS (CTO's consolidation) ==========

@router_finish_setup.callback_query(F.data.startswith("fs:dyad:about:"))
async def fs_dyad_about(callback: CallbackQuery):
    """Show dyad information and consent."""
    await _safe_answer(callback)
    
    dyad_key = callback.data.split(":", 3)[-1]
    locale = get_locale(callback.message.chat.id)
    
    # Get dyad info
    dyad_info = dyad_registry.get_dyad(dyad_key)
    if not dyad_info:
        await callback.message.answer("❌ Dyad not found.")
        return
    
    # Get localized consent text
    raw_consent_text = dyad_info.get("consent_text", "")
    consent_text = get_localized_text(raw_consent_text, locale) or "_(no details provided)_"
    
    if locale == "pt_br":
        header = "Como este ajudante usa seus dados"
        accept_text = "Aceitar"
        decline_text = "Recusar"
        tip_text = "💡 Dica: Mantenha as dicas com ≤25 palavras para melhor experiência."
    else:
        header = "How this helper uses your data"
        accept_text = "Accept"
        decline_text = "Decline"
        tip_text = "💡 Tip: Keep tips ≤25 words for best experience."
    
    consent_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=accept_text,
                callback_data=f"fs:consent:accept:{dyad_key}"
            ),
            InlineKeyboardButton(
                text=decline_text,
                callback_data=f"fs:consent:decline:{dyad_key}"
            )
        ]
    ])
    
    await callback.message.edit_text(
        f"**{header}**\n\n{consent_text}\n\n{tip_text}",
        reply_markup=consent_keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


@router_finish_setup.callback_query(F.data.startswith("fs:dyad:launch:"))
async def fs_dyad_launch(callback: CallbackQuery):
    """Launch a dyad with PWA URL."""
    await _safe_answer(callback)
    
    dyad_key = callback.data.split(":", 3)[-1]
    locale = get_locale(callback.message.chat.id)
    
    # Get user's family
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        if locale == "pt_br":
            await callback.message.edit_text("❌ Nenhum perfil familiar encontrado.")
        else:
            await callback.message.edit_text("❌ No family found.")
        return
    
    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        if locale == "pt_br":
            await callback.message.edit_text("❌ Família não encontrada.")
        else:
            await callback.message.edit_text("❌ Family not found.")
        return
    
    # Check if dyad is enabled
    enabled_dyads = getattr(family, 'enabled_dyads', []) or []
    if dyad_key not in enabled_dyads:
        # Dyad not enabled - redirect to consent
        if locale == "pt_br":
            await callback.message.edit_text(
                "Este ajudante precisa do seu consentimento primeiro.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Revisar", callback_data=f"fs:consent:show:{dyad_key}")]
                ])
            )
        else:
            await callback.message.edit_text(
                "This helper needs your consent first.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Review", callback_data=f"fs:consent:show:{dyad_key}")]
                ])
            )
        return
    
    # Generate session token and PWA URL
    try:
        token = dyad_registry.generate_session_token(family_id, dyad_key, locale)
        pwa_url = _pwa_url(dyad_key, token)
        logger.info(f"Generated PWA URL for {dyad_key}: {pwa_url}")
        
        # Get dyad info for display
        dyad_info = dyad_registry.get_dyad(dyad_key)
        dyad_name = dyad_info.get("name", dyad_key.replace("_", " ").title()) if dyad_info else dyad_key.replace("_", " ").title()
        
        text = t(locale, "dyad_ready").format(dyad=h(dyad_name), mins=10)
        launch_text = t(locale, "btn_launch")
        info_text = t(locale, "btn_more")
        
        launch_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=launch_text, url=pwa_url),
                InlineKeyboardButton(text=info_text, callback_data=f"fs:dyad:about:{dyad_key}")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=launch_keyboard)
        
        logger.info(f"dyad_launch dyad={dyad_key} family={family_id} token_issued=1")
        
    except Exception as e:
        logger.error(f"Failed to create dyad launch URL: {e}")
        if locale == "pt_br":
            await callback.message.edit_text("❌ Erro ao criar link do Dyad.")
        else:
            await callback.message.edit_text("❌ Error creating dyad link.")


# Debug catch-all for finish-setup (optional)
@router_finish_setup.callback_query(F.data.startswith("fs:"))
async def fs_catch_all(callback: CallbackQuery):
    """Catch-all for unhandled fs: callbacks."""
    logger.warning(f"FS_CATCHALL data={callback.data}")
    await _safe_answer(callback, text="⚙️ Received")
