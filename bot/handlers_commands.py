from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from loguru import logger
from .profiles import profiles
from .families import families
from .dyad_registry import dyad_registry
from .i18n import get_locale
from .reason_client import create_reasoner_config
import json
from datetime import datetime
from pathlib import Path

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
        if locale == "pt_br":
            text = "❌ Nenhum perfil familiar encontrado. Complete o onboarding primeiro."
        else:
            text = "❌ No family profile found. Please complete onboarding first."
        await message.answer(text)
        return
    
    family_id = profile["family_id"]
    
    # Get recent insights from storage
    from .storage import storage
    recent_events = storage.get_recent_events(family_id, limit=3, event_types=["insight"])
    
    if not recent_events:
        if locale == "pt_br":
            text = "📊 **Insights Recentes**\n\nNenhum insight disponível ainda. Use os Dyads para gerar insights."
        else:
            text = "📊 **Recent Insights**\n\nNo insights available yet. Use Dyads to generate insights."
        await message.answer(text)
        return
    
    if locale == "pt_br":
        text = "📊 **Insights Recentes**\n\n"
    else:
        text = "📊 **Recent Insights**\n\n"
    
    for i, event in enumerate(recent_events, 1):
        text += f"{i}. {event.get('description', 'No description')}\n"
        text += f"   📅 {event.get('ts', 'Unknown time')}\n\n"
    
    await message.answer(text)


@router_commands.message(Command("reasoning"))
async def reasoning_command(message: Message):
    """Toggle AI reasoning on/off."""
    locale = get_locale(message.chat.id)
    
    # Get user profile
    profile = profiles.get_profile_by_chat_sync(message.chat.id)
    if not profile or not profile.get("family_id"):
        if locale == "pt_br":
            text = "❌ Nenhum perfil familiar encontrado. Complete o onboarding primeiro."
        else:
            text = "❌ No family profile found. Please complete onboarding first."
        await message.answer(text)
        return
    
    family_id = profile["family_id"]
    
    # Get current family
    family = await families.get_family(family_id)
    if not family:
        if locale == "pt_br":
            text = "❌ Família não encontrada."
        else:
            text = "❌ Family not found."
        await message.answer(text)
        return
    
    # Toggle reasoning
    current_reasoning = family.cloud_reasoning
    new_reasoning = not current_reasoning
    
    # Update family
    await families.upsert_fields(family_id, cloud_reasoning=new_reasoning)
    
    if locale == "pt_br":
        if new_reasoning:
            text = "✅ **IA Ativada**\n\nInsights com IA estão agora ativos para sua família."
        else:
            text = "❌ **IA Desativada**\n\nInsights com IA estão agora desativados para sua família."
    else:
        if new_reasoning:
            text = "✅ **AI Enabled**\n\nAI-powered insights are now active for your family."
        else:
            text = "❌ **AI Disabled**\n\nAI-powered insights are now disabled for your family."
    
    await message.answer(text)


@router_commands.message(Command("familyprofile"))
async def familyprofile_command(message: Message):
    """Show family profile mini dashboard."""
    locale = get_locale(message.chat.id)
    
    # Get user profile
    profile = profiles.get_profile_by_chat_sync(message.chat.id)
    if not profile or not profile.get("family_id"):
        if locale == "pt_br":
            text = "❌ Nenhum perfil familiar encontrado. Complete o onboarding primeiro."
        else:
            text = "❌ No family profile found. Please complete onboarding first."
        await message.answer(text)
        return
    
    family_id = profile["family_id"]
    
    # Get family details
    family = await families.get_family(family_id)
    if not family:
        if locale == "pt_br":
            text = "❌ Família não encontrada."
        else:
            text = "❌ Family not found."
        await message.answer(text)
        return
    
    # Build profile text
    if locale == "pt_br":
        text = f"👨‍👩‍👧‍👦 **Perfil da Família**\n\n"
        text += f"**ID da Família:** `{family.family_id}`\n"
        text += f"**Pai/Mãe:** {family.parent_name}\n"
        text += f"**Crianças:** {len(family.children)}\n"
        text += f"**Membros:** {len(family.members)}\n"
        text += f"**Dyads Ativos:** {len(family.enabled_dyads)}\n"
        text += f"**IA Ativa:** {'Sim' if family.cloud_reasoning else 'Não'}\n"
        
        edit_text = "✏️ Editar Membros"
        sessions_text = "📊 Sessões"
        tags_text = "🏷️ Tags"
        generate_code_text = "🔗 Gerar Código"
    else:
        text = f"👨‍👩‍👧‍👦 **Family Profile**\n\n"
        text += f"**Family ID:** `{family.family_id}`\n"
        text += f"**Parent:** {family.parent_name}\n"
        text += f"**Children:** {len(family.children)}\n"
        text += f"**Members:** {len(family.members)}\n"
        text += f"**Active Dyads:** {len(family.enabled_dyads)}\n"
        text += f"**AI Active:** {'Yes' if family.cloud_reasoning else 'No'}\n"
        
        edit_text = "✏️ Edit Members"
        sessions_text = "📊 Sessions"
        tags_text = "🏷️ Tags"
        generate_code_text = "🔗 Generate Code"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=edit_text, callback_data="family:edit_members")],
        [InlineKeyboardButton(text=sessions_text, callback_data="family:view_sessions")],
        [InlineKeyboardButton(text=tags_text, callback_data="family:view_tags")],
        [InlineKeyboardButton(text=generate_code_text, callback_data="family:generate_code")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router_commands.message(Command("summondyad"))
async def summondyad_command(message: Message):
    """Show inline list of enabled Dyads."""
    locale = get_locale(message.chat.id)
    
    # Get user profile
    profile = profiles.get_profile_by_chat_sync(message.chat.id)
    if not profile or not profile.get("family_id"):
        if locale == "pt_br":
            text = "❌ Nenhum perfil familiar encontrado. Complete o onboarding primeiro."
        else:
            text = "❌ No family profile found. Please complete onboarding first."
        await message.answer(text)
        return
    
    family_id = profile["family_id"]
    
    # Get family details
    family = await families.get_family(family_id)
    if not family:
        if locale == "pt_br":
            text = "❌ Família não encontrada."
        else:
            text = "❌ Family not found."
        await message.answer(text)
        return
    
    if not family.enabled_dyads:
        if locale == "pt_br":
            text = "❌ Nenhum Dyad ativado. Use /familyprofile para ativar Dyads."
        else:
            text = "❌ No Dyads enabled. Use /familyprofile to enable Dyads."
        await message.answer(text)
        return
    
    if locale == "pt_br":
        text = "🎯 **Dyads Disponíveis**\n\nEscolha um Dyad para iniciar:"
    else:
        text = "🎯 **Available Dyads**\n\nChoose a Dyad to start:"
    
    # Create buttons for enabled Dyads
    keyboard_buttons = []
    for dyad_id in family.enabled_dyads:
        dyad_info = dyad_registry.get_dyad(dyad_id)
        if dyad_info:
            dyad_name = dyad_info.get("name", dyad_id)
            icon = dyad_info.get("icon", "🎯")
            button_text = f"{icon} {dyad_name}"
            keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"dyad:summon:{dyad_id}")])
    
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


# Callback handlers for command buttons
@router_commands.callback_query(F.data.startswith("dyad:summon:"))
async def handle_dyad_summon(callback: CallbackQuery):
    """Handle Dyad summoning from command."""
    await callback.answer()
    
    dyad_id = callback.data.split(":")[2]
    locale = get_locale(callback.message.chat.id)
    
    # Get user profile
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        if locale == "pt_br":
            text = "❌ Nenhum perfil familiar encontrado."
        else:
            text = "❌ No family profile found."
        await callback.message.edit_text(text)
        return
    
    family_id = profile["family_id"]
    
    # Create Dyad URL
    try:
        dyad_url = dyad_registry.create_dyad_url(family_id, dyad_id, locale)
        
        dyad_info = dyad_registry.get_dyad(dyad_id)
        dyad_name = dyad_info.get("name", dyad_id) if dyad_info else dyad_id
        
        if locale == "pt_br":
            text = f"🎯 **{dyad_name}**\n\nClique no link abaixo para iniciar:"
        else:
            text = f"🎯 **{dyad_name}**\n\nClick the link below to start:"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Launch", url=dyad_url)]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Failed to create Dyad URL: {e}")
        if locale == "pt_br":
            text = "❌ Erro ao criar link do Dyad."
        else:
            text = "❌ Error creating Dyad link."
        await callback.message.edit_text(text)
