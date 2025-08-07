from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from .profiles import profiles
from .families import families
from .i18n import get_locale

router_family_link = Router()


class FamilyLink(StatesGroup):
    """FSM states for family linking flow."""
    join_code = State()


@router_family_link.callback_query(F.data == "family:link")
async def handle_family_link_start(callback: CallbackQuery, state: FSMContext):
    """Start the family linking process."""
    await callback.answer()
    
    locale = get_locale(callback.message.chat.id)
    
    if locale == "pt_br":
        text = "Digite o código de convite da sua família:"
        placeholder = "Ex: ABC123"
    else:
        text = "Enter your family's invite code:"
        placeholder = "e.g., ABC123"
    
    await state.set_state(FamilyLink.join_code)
    await callback.message.edit_text(text)


@router_family_link.message(FamilyLink.join_code)
async def handle_join_code_input(message: Message, state: FSMContext):
    """Handle join code input and attempt to link family."""
    join_code = message.text.strip().upper()
    
    locale = get_locale(message.chat.id)
    
    try:
        # Attempt to consume the join code
        family_profile = await families.consume_join_code(join_code, message.chat.id)
        
        if family_profile:
            # Update user profile to link to family
            profiles.upsert_fields_sync(message.chat.id, {
                "family_id": family_profile.family_id,
                "status": "active"
            })
            
            if locale == "pt_br":
                success_text = f"✅ Conectado com sucesso à família!\n\nID da Família: `{family_profile.family_id}`\n\nAgora vamos configurar os Dyads disponíveis."
            else:
                success_text = f"✅ Successfully linked to family!\n\nFamily ID: `{family_profile.family_id}`\n\nNow let's set up available Dyads."
            
            await message.answer(success_text)
            
            # Show Dyad selection
            await show_dyad_selection(message)
            
        else:
            if locale == "pt_br":
                error_text = "❌ Código de convite inválido ou expirado. Tente novamente ou peça um novo código."
            else:
                error_text = "❌ Invalid or expired invite code. Try again or request a new code."
            
            await message.answer(error_text)
            return
            
    except Exception as e:
        logger.error(f"Error linking family: {e}")
        if locale == "pt_br":
            error_text = "❌ Erro ao conectar à família. Tente novamente."
        else:
            error_text = "❌ Error linking to family. Please try again."
        
        await message.answer(error_text)
        return
    
    # Clear FSM state
    await state.clear()


async def show_dyad_selection(message: Message):
    """Show Dyad selection for the family."""
    locale = get_locale(message.chat.id)
    
    if locale == "pt_br":
        text = "Quais Dyads você gostaria de ativar?"
        night_text = "🌙 Auxiliar da Noite"
        meal_text = "🍽️ Companheiro do Humor das Refeições"
        tantrum_text = "😤 Tradutor de Birras"
        continue_text = "Continuar"
    else:
        text = "Which Dyads would you like to enable?"
        night_text = "🌙 Night Helper"
        meal_text = "🍽️ Meal Mood Companion"
        tantrum_text = "😤 Tantrum Translator"
        continue_text = "Continue"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=night_text, callback_data="dyad:night_helper")],
        [InlineKeyboardButton(text=meal_text, callback_data="dyad:meal_mood")],
        [InlineKeyboardButton(text=tantrum_text, callback_data="dyad:tantrum_translator")],
        [InlineKeyboardButton(text=continue_text, callback_data="dyad:continue")]
    ])
    
    await message.answer(text, reply_markup=keyboard)
