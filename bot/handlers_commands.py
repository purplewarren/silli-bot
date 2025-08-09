from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger
from .profiles import profiles
from .families import families
from .dyad_registry import dyad_registry
from .i18n import get_locale, t
from .utils.text import b, h
from .reason_client import client
import json
from datetime import datetime
from pathlib import Path
import asyncio

router_commands = Router()


@router_commands.message(Command("about"))
async def about_command(message: Message):
    """Re-run the Silli road-show."""
    locale = get_locale(message.chat.id)
    
    # Import here to avoid circular imports
    from .handlers_onboarding import start_roadshow
    from aiogram.fsm.context import FSMContext
    
    # Create a mock state context
    class MockState:
        async def set_state(self, state):
            pass
        async def update_data(self, **kwargs):
            pass
        async def get_data(self):
            return {}
        async def clear(self):
            pass
    
    state = MockState()
    await start_roadshow(message, state)


@router_commands.message(Command("insights"))
async def insights_command(message: Message):
    """Pull 3 latest proactive insights."""
    locale = get_locale(message.chat.id)
    
        # Get user profile
    profile = profiles.get_profile_by_chat_sync(message.chat.id)
    if not profile or not profile.get("family_id"):
        text = t(locale, "err_status")
        await message.answer(text)
        return

    family_id = profile["family_id"]

    # Get recent insights from storage
    from .storage import storage
    recent_events = storage.get_recent_events(family_id, limit=3, event_types=["insight"])
    
    if not recent_events:
        if locale == "pt_br":
            text = "📊 <b>Insights Recentes</b>\n\nNenhum insight disponível ainda. Use os Dyads para gerar insights."
        else:
            text = "📊 <b>Recent Insights</b>\n\nNo insights available yet. Use Dyads to generate insights."
        await message.answer(text)
        return
    
    if locale == "pt_br":
        text = "📊 <b>Insights Recentes</b>\n\n"
    else:
        text = "📊 <b>Recent Insights</b>\n\n"
    
    for i, event in enumerate(recent_events, 1):
        text += f"{i}. {event.get('description', 'No description')}\n"
        text += f"   📅 {event.get('ts', 'Unknown time')}\n\n"
    
    await message.answer(text)


@router_commands.message(Command("help"))
async def help_command(message: Message):
    """Show clean, organized command help."""
    from .strings import COPY, BRAND_NAME
    locale = get_locale(message.chat.id)
    
    if locale == "pt_br":
        help_text = (
            f"✨ {b(BRAND_NAME)} — Seu Companheiro de Paternidade\n\n"
            f"{COPY['help_header']}\n\n"
            f"{b('Comandos:')}\n"
            "• /familyprofile — painel da família\n"
            "• /summondyad — abrir ajudantes\n"
            "• /reasoning — ativar/desativar ME\n\n"
            f"{b('Outros:')}\n"
            "• /about — apresentação do Silli\n"
            "• /feedback — enviar feedback\n\n"
            f"{b('Como Usar:')}\n"
            "Digite naturalmente ou use os comandos acima."
        )
    else:
        help_text = (
            f"✨ {b(BRAND_NAME)} — Your Parenting Companion\n\n"
            f"{COPY['help_header']}\n\n"
            f"{b('Commands:')}\n"
            "• /familyprofile — family dashboard\n"
            "• /summondyad — launch helpers\n"
            "• /reasoning — toggle ME\n\n"
            f"{b('Others:')}\n"
            "• /about — Silli roadshow\n"
            "• /feedback — send feedback"
        )
    
    await message.answer(help_text)


@router_commands.message(Command("ops_reason_stats"))
async def ops_reason_stats(message: Message):
    """Show AI reasoning performance metrics."""
    from .admin import is_admin
    
    # Check admin access
    if not is_admin(message.from_user.id):
        await message.answer("Command not available.", parse_mode="HTML")
        return
    
    from .metrics import metrics
    import json
    
    # Get current metrics snapshot
    stats = metrics.snapshot()
    
    # Format as JSON in code block
    stats_json = json.dumps(stats, indent=2)
    
    # Calculate additional derived metrics
    success_rate = (stats["ok"] / stats["n"] * 100) if stats["n"] > 0 else 0
    
    response_text = (
        f"<b>ME Performance (5min window)</b>\n\n"
        f"<code>{stats_json}</code>\n\n"
        f"📊 <b>Summary:</b>\n"
        f"• Success Rate: {success_rate:.1f}%\n"
        f"• Total Calls: {stats['n']}\n"
        f"• Median Latency: {stats['p50']}ms\n"
        f"• P95 Latency: {stats['p95']}ms"
    )
    
    await message.answer(response_text, parse_mode="HTML")


@router_commands.message(Command("reasoning"))
async def reasoning_command(message: Message):
    """Toggle AI reasoning on/off."""
    logger.info(f"🔧 REASONING command received from chat {message.chat.id}")
    locale = get_locale(message.chat.id)
    
    # Get user profile
    logger.info(f"🔧 Getting profile for chat {message.chat.id}")
    profile = profiles.get_profile_by_chat_sync(message.chat.id)
    if not profile or not profile.get("family_id"):
        logger.info(f"🔧 No profile or family_id for chat {message.chat.id}")
        text = t(locale, "err_status")
        await message.answer(text)
        return

    family_id = profile["family_id"]
    logger.info(f"🔧 Found family_id: {family_id}")

    # Get current family
    family = families.get_family(family_id)
    if not family:
        logger.info(f"🔧 No family found for family_id: {family_id}")
        text = t(locale, "err_status")
        await message.answer(text)
        return
    
    # Toggle reasoning
    current_reasoning = family.cloud_reasoning
    new_reasoning = not current_reasoning
    logger.info(f"🔧 Toggling AI: {current_reasoning} -> {new_reasoning}")
    
    # Update family - direct approach
    try:
        # Get the current family data
        current_data = families._read()
        if family_id in current_data:
            # Update the cloud_reasoning field directly
            current_data[family_id]["cloud_reasoning"] = new_reasoning
            current_data[family_id]["updated_at"] = datetime.now().isoformat()
            families._write(current_data)
            logger.info(f"🔧 Successfully updated family reasoning")
        else:
            logger.error(f"🔧 Family not found in data: {family_id}")
            await message.answer("Family not found")
            return
    except Exception as e:
        logger.error(f"🔧 Error updating family: {e}")
        await message.answer("Error updating AI settings")
        return
    
    # Log the action
    logger.info(f"reasoner_toggle family={family_id} user={message.chat.id} value={'on' if new_reasoning else 'off'}")
    
    if new_reasoning:
        text = "🧠 ME (20B) is on. Tips may be richer." if locale == "en" else "🧠 ME (20B) está ativo. Dicas podem ser mais ricas."
    else:
        text = "🧠 ME (20B) is off. You'll get basic tips only." if locale == "en" else "🧠 ME (20B) está desativado. Você receberá apenas dicas básicas."
    
    await message.answer(text)


@router_commands.message(Command("familyprofile"))
async def familyprofile_command(message: Message):
    """Show family profile mini dashboard."""
    logger.info(f"👪 FAMILYPROFILE command received from chat {message.chat.id}")
    locale = get_locale(message.chat.id)
    
    # Get user profile
    profile = profiles.get_profile_by_chat_sync(message.chat.id)
    if not profile or not profile.get("family_id"):
        text = t(locale, "err_status")
        await message.answer(text)
        return

    family_id = profile["family_id"]

    # Get family details
    family = families.get_family(family_id)
    if not family:
        text = t(locale, "err_status")
        await message.answer(text)
        return
    
    # Build profile text
    header = t(locale, "family_title").format(org="Silli")
    ai_text = ("Sim" if family.cloud_reasoning else "Não") if locale=="pt_br" else ("Yes" if family.cloud_reasoning else "No")
    
    stats = t(locale, "family_stats").format(
        bold_open="<b>", bold_close="</b>",
        fid=h(family.family_id),
        parent=h(family.parent_name),
        children=len(family.children),
        members=len(family.members),
        dyads=len(family.enabled_dyads),
        ai=ai_text
    )
    text = f"{b(header)}\n\n{stats}"
    
    # Check if setup is incomplete
    enabled_dyads = getattr(family, 'enabled_dyads', []) or []
    cloud_reasoning = getattr(family, 'cloud_reasoning', False)
    
    # Build interactive buttons
    keyboard_buttons = []
    
    # Add Finish Setup button if setup is incomplete
    if not enabled_dyads or not cloud_reasoning:
        finish_setup_text = t(locale, "finish_header")
        keyboard_buttons.append([InlineKeyboardButton(text=finish_setup_text, callback_data="finish:open")])
    
    # Add dyad management buttons if dyads are enabled
    if enabled_dyads:
        dyad_text = "🧬 Gerenciar Dyads" if locale == "pt_br" else "🧬 Manage Dyads"
        keyboard_buttons.append([InlineKeyboardButton(text=dyad_text, callback_data="family:dyads")])
    
    # Add family profile management button
    family_text = "👪 Gerenciar Perfil Familiar" if locale == "pt_br" else "👪 Manage Family Profile"
    keyboard_buttons.append([InlineKeyboardButton(text=family_text, callback_data="family:manage")])
    
    # Add ME (Memetic Engine) toggle button
    if cloud_reasoning:
        me_text = "🧠 Desativar ME" if locale == "pt_br" else "🧠 Disable ME"
        callback_data = "family:me:disable"
    else:
        me_text = "🧠 Ativar ME" if locale == "pt_br" else "🧠 Enable ME"
        callback_data = "family:me:enable"
    
    keyboard_buttons.append([InlineKeyboardButton(text=me_text, callback_data=callback_data)])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(text, reply_markup=keyboard)


# Family profile button handlers
@router_commands.callback_query(F.data == "family:dyads")
async def family_dyads_callback(callback: CallbackQuery):
    """Handle comprehensive dyad management from family profile."""
    await callback.answer()
    
    chat_id = callback.message.chat.id
    locale = get_locale(chat_id)
    
    # Get user profile and family
    profile = profiles.get_profile_by_chat_sync(chat_id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer(t(locale, "err_status"))
        return

    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer(t(locale, "err_status"))
        return
    
    # Get all available dyads and family's enabled dyads
    all_dyads = dyad_registry.get_all_dyads()
    enabled_dyads = set(getattr(family, 'enabled_dyads', []) or [])
    
    # Build the comprehensive dyad management interface
    if locale == "pt_br":
        header = "🧬 **Gerenciar Dyads**\n\n"
        enabled_section = "✅ **Dyads Ativados:**\n"
        available_section = "\n🔓 **Dyads Disponíveis:**\n"
        no_enabled = "Nenhum dyad ativado ainda.\n"
        no_available = "Todos os dyads estão ativados!"
    else:
        header = "🧬 **Manage Dyads**\n\n"
        enabled_section = "✅ **Enabled Dyads:**\n"
        available_section = "\n🔓 **Available Dyads:**\n"
        no_enabled = "No dyads enabled yet.\n"
        no_available = "All dyads are enabled!"
    
    text = header
    keyboard_buttons = []
    
    # Show enabled dyads with launch and disable buttons
    if enabled_dyads:
        text += enabled_section
        for dyad_id in enabled_dyads:
            dyad_data = all_dyads.get(dyad_id, {})
            dyad_name = dyad_data.get("name", dyad_id.replace('_', ' ').title())
            text += f"• {dyad_name}\n"
            
            # Add buttons for each enabled dyad
            launch_text = "🚀 Launch" if locale == "en" else "🚀 Abrir"
            disable_text = "❌ Disable" if locale == "en" else "❌ Desativar"
            
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"{launch_text} {dyad_name}", callback_data=f"fs:dyad:launch:{dyad_id}"),
                InlineKeyboardButton(text=disable_text, callback_data=f"dyad:disable:{dyad_id}")
            ])
    else:
        text += no_enabled
    
    # Show available dyads with enable buttons
    available_dyads = [dyad_id for dyad_id in all_dyads.keys() if dyad_id not in enabled_dyads]
    
    if available_dyads:
        text += available_section
        for dyad_id in available_dyads:
            dyad_data = all_dyads.get(dyad_id, {})
            dyad_name = dyad_data.get("name", dyad_id.replace('_', ' ').title())
            description = dyad_data.get("description", "")
            text += f"• {dyad_name}\n"
            if description:
                text += f"  _{description}_\n"
            
            # Add enable button
            enable_text = "✅ Enable" if locale == "en" else "✅ Ativar"
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"{enable_text} {dyad_name}", callback_data=f"dyad:enable:{dyad_id}")
            ])
    else:
        if enabled_dyads:  # Only show this if there are enabled dyads
            text += f"\n{no_available}"
    
    # Add back button
    back_text = "◀️ Back" if locale == "en" else "◀️ Voltar"
    keyboard_buttons.append([InlineKeyboardButton(text=back_text, callback_data="family:back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await callback.message.edit_text(text, reply_markup=keyboard)


@router_commands.callback_query(F.data.startswith("dyad:enable:"))
async def dyad_enable_callback(callback: CallbackQuery):
    """Handle enabling a dyad."""
    await callback.answer()
    
    dyad_id = callback.data.split(":", 2)[-1]
    chat_id = callback.message.chat.id
    locale = get_locale(chat_id)
    
    # Get user profile and family
    profile = profiles.get_profile_by_chat_sync(chat_id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer(t(locale, "err_status"))
        return

    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer(t(locale, "err_status"))
        return
    
    # Enable the dyad
    try:
        current_data = families._read()
        if family_id in current_data:
            enabled_dyads = set(current_data[family_id].get("enabled_dyads", []))
            enabled_dyads.add(dyad_id)
            current_data[family_id]["enabled_dyads"] = list(enabled_dyads)
            current_data[family_id]["updated_at"] = datetime.now().isoformat()
            families._write(current_data)
            
            # Get dyad name for confirmation
            dyad_data = dyad_registry.get_dyad(dyad_id)
            dyad_name = dyad_data.get("name", dyad_id.replace('_', ' ').title()) if dyad_data else dyad_id
            
            # Show confirmation
            if locale == "pt_br":
                text = f"✅ {dyad_name} foi ativado!"
            else:
                text = f"✅ {dyad_name} has been enabled!"
            
            await callback.message.answer(text)
            
            logger.info(f"Dyad enabled: {dyad_id} for family {family_id}")
            
            # Refresh the dyad management interface
            await family_dyads_callback(callback)
            
        else:
            await callback.message.answer("Family not found")
    except Exception as e:
        logger.error(f"Error enabling dyad {dyad_id}: {e}")
        await callback.message.answer("Error enabling dyad")


@router_commands.callback_query(F.data.startswith("dyad:disable:"))
async def dyad_disable_callback(callback: CallbackQuery):
    """Handle disabling a dyad."""
    await callback.answer()
    
    dyad_id = callback.data.split(":", 2)[-1]
    chat_id = callback.message.chat.id
    locale = get_locale(chat_id)
    
    # Get user profile and family
    profile = profiles.get_profile_by_chat_sync(chat_id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer(t(locale, "err_status"))
        return

    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer(t(locale, "err_status"))
        return
    
    # Disable the dyad
    try:
        current_data = families._read()
        if family_id in current_data:
            enabled_dyads = set(current_data[family_id].get("enabled_dyads", []))
            enabled_dyads.discard(dyad_id)  # Remove if present
            current_data[family_id]["enabled_dyads"] = list(enabled_dyads)
            current_data[family_id]["updated_at"] = datetime.now().isoformat()
            families._write(current_data)
            
            # Get dyad name for confirmation
            dyad_data = dyad_registry.get_dyad(dyad_id)
            dyad_name = dyad_data.get("name", dyad_id.replace('_', ' ').title()) if dyad_data else dyad_id
            
            # Show confirmation
            if locale == "pt_br":
                text = f"❌ {dyad_name} foi desativado."
            else:
                text = f"❌ {dyad_name} has been disabled."
            
            await callback.message.answer(text)
            
            logger.info(f"Dyad disabled: {dyad_id} for family {family_id}")
            
            # Refresh the dyad management interface
            await family_dyads_callback(callback)
            
        else:
            await callback.message.answer("Family not found")
    except Exception as e:
        logger.error(f"Error disabling dyad {dyad_id}: {e}")
        await callback.message.answer("Error disabling dyad")


@router_commands.callback_query(F.data.startswith("family:me:"))
async def family_me_toggle_callback(callback: CallbackQuery):
    """Handle ME (Memetic Engine) toggle from family profile."""
    await callback.answer()
    
    action = callback.data.split(":")[-1]  # "enable" or "disable"
    chat_id = callback.message.chat.id
    locale = get_locale(chat_id)
    
    # Get user profile
    profile = profiles.get_profile_by_chat_sync(chat_id)
    if not profile or not profile.get("family_id"):
        await callback.message.answer(t(locale, "err_status"))
        return

    family_id = profile["family_id"]
    family = families.get_family(family_id)
    if not family:
        await callback.message.answer(t(locale, "err_status"))
        return
    
    # Toggle ME (using the same direct approach as /reasoning command)
    new_reasoning = (action == "enable")
    try:
        current_data = families._read()
        if family_id in current_data:
            current_data[family_id]["cloud_reasoning"] = new_reasoning
            current_data[family_id]["updated_at"] = datetime.now().isoformat()
            families._write(current_data)
        else:
            await callback.message.answer("Family not found")
            return
    except Exception as e:
        logger.error(f"Error updating family ME: {e}")
        await callback.message.answer("Error updating ME settings")
        return
    
    # Log the action
    logger.info(f"ME_toggle family={family_id} user={chat_id} action={action}")
    
    # Send confirmation
    if new_reasoning:
        text = "🧠 ME ativado!" if locale == "pt_br" else "🧠 ME enabled!"
    else:
        text = "🧠 ME desativado!" if locale == "pt_br" else "🧠 ME disabled!"
    
    await callback.message.answer(text)
    
    # Refresh the family profile
    class MockMessage:
        def __init__(self, chat_id):
            self.chat = type('Chat', (), {'id': chat_id})()
            
        async def answer(self, text, reply_markup=None):
            await callback.message.edit_text(text, reply_markup=reply_markup)
    
    mock_message = MockMessage(chat_id)
    await familyprofile_command(mock_message)


@router_commands.callback_query(F.data == "family:manage")
async def family_manage_callback(callback: CallbackQuery):
    """Handle family profile management from family profile."""
    await callback.answer()
    
    chat_id = callback.message.chat.id
    locale = get_locale(chat_id)
    
    # Show family management options
    if locale == "pt_br":
        text = "👪 **Gerenciar Perfil Familiar**\n\nEscolha uma opção:"
        edit_text = "✏️ Editar Informações"
        members_text = "👥 Gerenciar Membros"
        children_text = "👶 Gerenciar Filhos"
    else:
        text = "👪 **Manage Family Profile**\n\nChoose an option:"
        edit_text = "✏️ Edit Information"
        members_text = "👥 Manage Members"
        children_text = "👶 Manage Children"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=edit_text, callback_data="family:edit")],
        [InlineKeyboardButton(text=members_text, callback_data="family:members")],
        [InlineKeyboardButton(text=children_text, callback_data="family:children")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="family:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


@router_commands.callback_query(F.data == "family:back")
async def family_back_callback(callback: CallbackQuery):
    """Handle back button from family management."""
    await callback.answer()
    
    # Go back to family profile
    chat_id = callback.message.chat.id
    class MockMessage:
        def __init__(self, chat_id):
            self.chat = type('Chat', (), {'id': chat_id})()
            
        async def answer(self, text, reply_markup=None):
            await callback.message.edit_text(text, reply_markup=reply_markup)
    
    mock_message = MockMessage(chat_id)
    await familyprofile_command(mock_message)


@router_commands.message(Command("summondyad"))
async def summondyad_command(message: Message):
    """Show inline list of enabled Dyads."""
    logger.info(f"🔧 SUMMONDYAD command received from chat {message.chat.id}")
    locale = get_locale(message.chat.id)
    
    # Get user profile
    profile = profiles.get_profile_by_chat_sync(message.chat.id)
    if not profile or not profile.get("family_id"):
        text = t(locale, "err_status")
        await message.answer(text)
        return

    family_id = profile["family_id"]

    # Get family details
    family = families.get_family(family_id)
    if not family:
        text = t(locale, "err_status")
        await message.answer(text)
        return
    
    if not family.enabled_dyads:
        text = t(locale, "dyads_empty")
        await message.answer(text)
        return
    
    title = b(t(locale, "dyads_available_title"))
    subtitle = t(locale, "dyads_choose")
    text = f"{title}\n\n{subtitle}"
    
    # Create buttons for enabled Dyads
    keyboard_buttons = []
    for dyad_id in family.enabled_dyads:
        dyad_info = dyad_registry.get_dyad(dyad_id)
        if dyad_info:
            dyad_name = dyad_info.get("name", dyad_id)
            icon = dyad_info.get("icon", "🎯")
            button_text = f"{icon} {dyad_name}"
            keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"fs:dyad:launch:{dyad_id}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(text, reply_markup=keyboard)


@router_commands.message(Command("feedback"))
async def feedback_command(message: Message):
    """Store free-text feedback."""
    locale = get_locale(message.chat.id)
    
    # Extract feedback text (everything after /feedback)
    feedback_text = message.text.replace("/feedback", "").strip()
    
    if not feedback_text:
        if locale == "pt_br":
            text = "📝 **Enviar Feedback**\n\nUse `/feedback <sua mensagem>` para enviar feedback.\n\nExemplo: `/feedback O bot está funcionando muito bem!`"
        else:
            text = "📝 **Send Feedback**\n\nUse `/feedback <your message>` to send feedback.\n\nExample: `/feedback The bot is working great!`"
        await message.answer(text)
        return
    
    # Store feedback
    feedback_data = {
        "timestamp": datetime.now().isoformat(),
        "chat_id": message.chat.id,
        "feedback": feedback_text,
        "user_info": {
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "username": message.from_user.username
        }
    }
    
    try:
        # Save to feedback file
        feedback_file = Path("data/feedback.jsonl")
        feedback_file.parent.mkdir(exist_ok=True)
        
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")
        
        if locale == "pt_br":
            text = "✅ **Feedback Enviado**\n\nObrigado pelo seu feedback! Ele foi salvo e será revisado pela equipe."
        else:
            text = "✅ **Feedback Sent**\n\nThank you for your feedback! It has been saved and will be reviewed by the team."
        
        await message.answer(text)
        
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        if locale == "pt_br":
            text = "❌ Erro ao salvar feedback. Tente novamente mais tarde."
        else:
            text = "❌ Error saving feedback. Please try again later."
        await message.answer(text)


@router_commands.message(Command("more"))
async def more_command(message: Message):
    """Show full legacy command list."""
    locale = get_locale(message.chat.id)
    
    if locale == "pt_br":
        text = "📋 **Comandos Legados**\n\n"
        text += "**Comandos Principais:**\n"
        text += "• `/start` - Iniciar onboarding\n"
        text += "• `/help` - Ver comandos disponíveis\n"
        text += "• `/lang` - Alterar idioma\n"
        text += "• `/about` - Re-executar apresentação\n"
        text += "• `/insights` - Ver insights recentes\n"
        text += "• `/reasoning` - Ativar/desativar IA\n"
        text += "• `/familyprofile` - Perfil da família\n"
        text += "• `/summondyad` - Listar Dyads\n"
        text += "• `/feedback` - Enviar feedback\n\n"
        
        text += "**Comandos de Dyad:**\n"
        text += "• `/summon_helper` - Escolher Dyad\n"
        text += "• `/summon_night_helper` - Auxiliar da Noite\n"
        text += "• `/summon_meal_mood` - Companheiro do Humor das Refeições\n"
        text += "• `/summon_tantrum_translator` - Tradutor de Birras\n\n"
        
        text += "**Comandos de Análise:**\n"
        text += "• `/analyze` - Enviar áudio para análise\n"
        text += "• `/ingest` - Fazer upload de sessão PWA\n"
        text += "• `/export` - Baixar dados\n\n"
        
        text += "**Comandos de IA:**\n"
        text += "• `/reason_on` - Ativar insights com IA\n"
        text += "• `/reason_off` - Desativar insights com IA\n"
        text += "• `/reason_status` - Status da IA\n"
        text += "• `/reason_stats` - Estatísticas da IA\n\n"
        
        text += "**Outros:**\n"
        text += "• `/privacy_offline` - Modo offline\n"
    else:
        text = "📋 **Legacy Commands**\n\n"
        text += "**Core Commands:**\n"
        text += "• `/start` - Start onboarding\n"
        text += "• `/help` - See available commands\n"
        text += "• `/lang` - Change language\n"
        text += "• `/about` - Re-run introduction\n"
        text += "• `/insights` - View recent insights\n"
        text += "• `/reasoning` - Toggle AI on/off\n"
        text += "• `/familyprofile` - Family profile\n"
        text += "• `/summondyad` - List Dyads\n"
        text += "• `/feedback` - Send feedback\n\n"
        
        text += "**Dyad Commands:**\n"
        text += "• `/summon_helper` - Choose Dyad\n"
        text += "• `/summon_night_helper` - Night Helper\n"
        text += "• `/summon_meal_mood` - Meal Mood Companion\n"
        text += "• `/summon_tantrum_translator` - Tantrum Translator\n\n"
        
        text += "**Analysis Commands:**\n"
        text += "• `/analyze` - Send audio for analysis\n"
        text += "• `/ingest` - Upload PWA session\n"
        text += "• `/export` - Download data\n\n"
        
        text += "**AI Commands:**\n"
        text += "• `/reason_on` - Enable AI insights\n"
        text += "• `/reason_off` - Disable AI insights\n"
        text += "• `/reason_status` - AI status\n"
        text += "• `/reason_stats` - AI statistics\n\n"
        
        text += "**Other:**\n"
        text += "• `/privacy_offline` - Offline mode\n"
    
    await message.answer(text)


@router_commands.message(Command("scheduler"))
async def scheduler_command(message: Message):
    """Show scheduler status and controls."""
    locale = get_locale(message.chat.id)
    
    # Get scheduler status
    from .scheduler import get_scheduler_status
    status = get_scheduler_status()
    
    if locale == "pt_br":
        text = "⏰ **Status do Agendador Proativo**\n\n"
        text += f"**Status:** {'🟢 Ativo' if status['running'] else '🔴 Inativo'}\n"
        text += f"**Intervalo:** {status['interval_hours']} horas\n"
        text += f"**Famílias com insights:** {len(status['last_insight_times'])}\n\n"
        
        if status['last_insight_times']:
            text += "**Últimos insights enviados:**\n"
            for family_id, last_time in list(status['last_insight_times'].items())[:5]:
                text += f"• {family_id}: {last_time}\n"
        
        start_text = "▶️ Iniciar"
        stop_text = "⏹️ Parar"
        test_text = "🧪 Testar Insight"
    else:
        text = "⏰ **Proactive Scheduler Status**\n\n"
        text += f"**Status:** {'🟢 Active' if status['running'] else '🔴 Inactive'}\n"
        text += f"**Interval:** {status['interval_hours']} hours\n"
        text += f"**Families with insights:** {len(status['last_insight_times'])}\n\n"
        
        if status['last_insight_times']:
            text += "**Last insights sent:**\n"
            for family_id, last_time in list(status['last_insight_times'].items())[:5]:
                text += f"• {family_id}: {last_time}\n"
        
        start_text = "▶️ Start"
        stop_text = "⏹️ Stop"
        test_text = "🧪 Test Insight"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=start_text, callback_data="scheduler:start"),
            InlineKeyboardButton(text=stop_text, callback_data="scheduler:stop")
        ],
        [InlineKeyboardButton(text=test_text, callback_data="scheduler:test")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


# Legacy dyad summon handler REMOVED - consolidated under finish_setup router with fs: prefix


# Debug catch-all for commands router
@router_commands.callback_query()
async def debug_commands_catchall(callback: CallbackQuery):
    """Debug catch-all for commands router."""
    logger.warning(f"[DEBUG COMMANDS] Unhandled callback: {callback.data}")
    await callback.answer("Debug: Commands router received callback")


@router_commands.callback_query(F.data.startswith("scheduler:"))
async def handle_scheduler_controls(callback: CallbackQuery):
    """Handle scheduler control callbacks."""
    await callback.answer()
    
    action = callback.data.split(":")[1]
    locale = get_locale(callback.message.chat.id)
    
    if action == "start":
        from .scheduler import scheduler
        if not scheduler.running:
            asyncio.create_task(scheduler.start())
            if locale == "pt_br":
                text = "✅ Agendador iniciado com sucesso!"
            else:
                text = "✅ Scheduler started successfully!"
        else:
            if locale == "pt_br":
                text = "ℹ️ Agendador já está ativo."
            else:
                text = "ℹ️ Scheduler is already running."
    
    elif action == "stop":
        from .scheduler import scheduler
        if scheduler.running:
            await scheduler.stop()
            if locale == "pt_br":
                text = "⏹️ Agendador parado com sucesso!"
            else:
                text = "⏹️ Scheduler stopped successfully!"
        else:
            if locale == "pt_br":
                text = "ℹ️ Agendador já está parado."
            else:
                text = "ℹ️ Scheduler is already stopped."
    
    elif action == "test":
        # Test insight generation for the user's family
        profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
        if not profile or not profile.get("family_id"):
            if locale == "pt_br":
                text = "❌ Nenhum perfil familiar encontrado."
            else:
                text = "❌ No family profile found."
        else:
            family_id = profile["family_id"]
            family = families.get_family(family_id)
            if not family:
                if locale == "pt_br":
                    text = "❌ Família não encontrada."
                else:
                    text = "❌ Family not found."
            else:
                # Generate a test insight
                from .scheduler import ProactiveScheduler
                test_scheduler = ProactiveScheduler()
                context = await test_scheduler.build_family_context(family)
                insight = await test_scheduler.generate_insight(family, context)
                
                if insight:
                    if locale == "pt_br":
                        text = f"🧪 **Insight de Teste**\n\n{insight}"
                    else:
                        text = f"🧪 **Test Insight**\n\n{insight}"
                else:
                    if locale == "pt_br":
                        text = "❌ Erro ao gerar insight de teste."
                    else:
                        text = "❌ Error generating test insight."
    
    else:
        if locale == "pt_br":
            text = "❌ Ação desconhecida."
        else:
            text = "❌ Unknown action."
    
    await callback.message.edit_text(text)
