from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger
from .profiles import profiles
from .families import families
from .i18n import get_locale
from datetime import datetime

router_family_create = Router()


@router_family_create.callback_query(F.data == "family:create")
async def handle_family_create_start(callback: CallbackQuery, state: FSMContext):
    """Start the family creation process."""
    await callback.answer()
    
    locale = get_locale(callback.message.chat.id)
    
    if locale == "pt_br":
        text = "Vamos criar sua família! Primeiro, qual é o seu nome?"
    else:
        text = "Let's create your family! First, what's your name?"
    
    # Import here to avoid circular imports
    from .handlers_onboarding import Onboarding
    await state.set_state(Onboarding.parent_name)
    await callback.message.edit_text(text)


@router_family_create.callback_query(F.data.startswith("dyad:"))
async def handle_dyad_toggle(callback: CallbackQuery):
    """Handle Dyad toggling for the family."""
    await callback.answer()
    
    dyad_id = callback.data.split(":")[1]
    
    if dyad_id == "continue":
        # Complete onboarding
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            text = "🎉 Parabéns! Seu perfil está configurado.\n\nUse /help para ver todos os comandos disponíveis."
        else:
            text = "🎉 Congratulations! Your profile is set up.\n\nUse /help to see all available commands."
        
        await callback.message.edit_text(text)
        return
    
    # Get current family profile
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        await callback.answer("❌ No family profile found")
        return
    
    family_id = profile["family_id"]
    
    # Toggle the dyad
    try:
        family = await families.get_family(family_id)
        if not family:
            await callback.answer("❌ Family not found")
            return
        
        enabled_dyads = set(family.enabled_dyads or [])
        
        if dyad_id in enabled_dyads:
            enabled_dyads.remove(dyad_id)
            action = "disabled"
        else:
            enabled_dyads.add(dyad_id)
            action = "enabled"
        
        # Update family with new dyad settings
        await families.upsert_fields(family_id, enabled_dyads=list(enabled_dyads))
        
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            dyad_names = {
                "night_helper": "Auxiliar da Noite",
                "meal_mood": "Companheiro do Humor das Refeições", 
                "tantrum_translator": "Tradutor de Birras"
            }
            dyad_name = dyad_names.get(dyad_id, dyad_id)
            await callback.answer(f"✅ {dyad_name} {'ativado' if action == 'enabled' else 'desativado'}")
        else:
            dyad_names = {
                "night_helper": "Night Helper",
                "meal_mood": "Meal Mood Companion",
                "tantrum_translator": "Tantrum Translator"
            }
            dyad_name = dyad_names.get(dyad_id, dyad_id)
            await callback.answer(f"✅ {dyad_name} {action}")
            
    except Exception as e:
        logger.error(f"Error toggling dyad {dyad_id}: {e}")
        await callback.answer("❌ Error updating dyad settings")


@router_family_create.callback_query(F.data == "family:generate_code")
async def handle_generate_join_code(callback: CallbackQuery):
    """Generate a join code for the family."""
    await callback.answer()
    
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            await callback.message.edit_text("❌ Nenhum perfil familiar encontrado.")
        else:
            await callback.message.edit_text("❌ No family profile found.")
        return
    
    family_id = profile["family_id"]
    
    try:
        # Generate join code
        join_code = await families.generate_join_code(family_id)
        
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            text = f"🔗 **Código de Convite da Família**\n\n`{join_code}`\n\nCompartilhe este código com outros membros da família para que eles possam se juntar.\n\n⚠️ Este código expira em 24 horas."
        else:
            text = f"🔗 **Family Invite Code**\n\n`{join_code}`\n\nShare this code with other family members so they can join.\n\n⚠️ This code expires in 24 hours."
        
        await callback.message.edit_text(text)
        
    except Exception as e:
        logger.error(f"Error generating join code: {e}")
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            await callback.message.edit_text("❌ Erro ao gerar código de convite.")
        else:
            await callback.message.edit_text("❌ Error generating invite code.")


@router_family_create.callback_query(F.data == "family:view_members")
async def handle_view_family_members(callback: CallbackQuery):
    """View family members."""
    await callback.answer()
    
    profile = profiles.get_profile_by_chat_sync(callback.message.chat.id)
    if not profile or not profile.get("family_id"):
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            await callback.message.edit_text("❌ Nenhum perfil familiar encontrado.")
        else:
            await callback.message.edit_text("❌ No family profile found.")
        return
    
    family_id = profile["family_id"]
    
    try:
        # Get family members
        members = await families.list_members(family_id)
        
        if not members:
            locale = get_locale(callback.message.chat.id)
            if locale == "pt_br":
                text = "👥 **Membros da Família**\n\nNenhum membro encontrado."
            else:
                text = "👥 **Family Members**\n\nNo members found."
        else:
            locale = get_locale(callback.message.chat.id)
            if locale == "pt_br":
                text = "👥 **Membros da Família**\n\n"
            else:
                text = "👥 **Family Members**\n\n"
            
            for i, member_id in enumerate(members, 1):
                text += f"{i}. `{member_id}`\n"
        
        await callback.message.edit_text(text)
        
    except Exception as e:
        logger.error(f"Error viewing family members: {e}")
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            await callback.message.edit_text("❌ Erro ao carregar membros da família.")
        else:
            await callback.message.edit_text("❌ Error loading family members.")
