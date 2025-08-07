from typing import Union
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from loguru import logger
from .i18n import get_locale

router_gate = Router()


async def show_greeting_card(event: Union[Message, CallbackQuery]) -> None:
    """Show the greeting card with Learn More and Access Family options."""
    locale = get_locale(event.chat.id)
    
    # Get localized text
    if locale == "pt_br":
        greeting_text = "Sou Silli. Escolha uma opção."
        learn_more_text = "Saiba Mais"
        access_family_text = "Acessar Família"
    else:
        greeting_text = "I'm Silli. Choose an option."
        learn_more_text = "Learn More"
        access_family_text = "Access Family"
    
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=learn_more_text, callback_data="gate:about"),
            InlineKeyboardButton(text=access_family_text, callback_data="gate:family")
        ]
    ])
    
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(greeting_text, reply_markup=keyboard)
    else:
        await event.answer(greeting_text, reply_markup=keyboard)


@router_gate.callback_query(F.data == "gate:about")
async def handle_gate_about(callback: CallbackQuery, state: FSMContext):
    """Handle Learn More callback - start the road-show."""
    await callback.answer()
    
    # Import here to avoid circular imports
    from .handlers_onboarding import start_roadshow
    await start_roadshow(callback.message, state)


@router_gate.callback_query(F.data == "gate:family")
async def handle_gate_family(callback: CallbackQuery, state: FSMContext):
    """Handle Access Family callback - show family options."""
    await callback.answer()
    
    locale = get_locale(callback.message.chat.id)
    
    if locale == "pt_br":
        text = "Como você gostaria de acessar sua família?"
        existing_text = "1️⃣ Já tenho uma família"
        create_text = "2️⃣ Criar uma nova família"
    else:
        text = "How would you like to access your family?"
        existing_text = "1️⃣ I already have a family"
        create_text = "2️⃣ Create a new family"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=existing_text, callback_data="family:link")],
        [InlineKeyboardButton(text=create_text, callback_data="family:create")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
