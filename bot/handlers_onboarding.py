from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from loguru import logger
from .profiles import profiles
from .i18n import get_locale, set_locale
from .storage import Storage, EventRecord
import json
from datetime import datetime

storage = Storage()
router_onboarding = Router()


class Onboarding(StatesGroup):
    """FSM states for onboarding flow."""
    # Road-show states
    roadshow_step = State()
    
    # Family creation states
    parent_name = State()
    has_partner = State()
    child_name = State()
    child_sex = State()
    child_age = State()
    health_notes = State()
    lifestyle_tags = State()
    other_children = State()
    pets = State()


# Road-show content
ROADSHOW_CONTENT = {
    "en": [
        "🚀 **Welcome to Silli**\n\nI'm your AI companion for family wellness. I help parents track and improve their children's daily routines.",
        "🎯 **What I Do**\n\n• Monitor sleep patterns and tantrum triggers\n• Analyze meal moods and nutrition insights\n• Provide personalized recommendations\n• Keep everything private and secure",
        "🔒 **Privacy First**\n\n• No raw audio leaves your device\n• All analysis happens locally\n• Your family data stays private\n• You control what's shared",
        "✨ **Ready to Start?**\n\nLet's set up your family profile to get personalized insights."
    ],
    "pt_br": [
        "🚀 **Bem-vindo ao Silli**\n\nSou seu companheiro de IA para o bem-estar familiar. Ajudo pais a rastrear e melhorar as rotinas diárias de seus filhos.",
        "🎯 **O Que Faço**\n\n• Monitoro padrões de sono e gatilhos de birra\n• Analiso humores das refeições e insights nutricionais\n• Forneço recomendações personalizadas\n• Mantenho tudo privado e seguro",
        "🔒 **Privacidade em Primeiro Lugar**\n\n• Nenhum áudio bruto sai do seu dispositivo\n• Toda análise acontece localmente\n• Seus dados familiares ficam privados\n• Você controla o que é compartilhado",
        "✨ **Pronto para Começar?**\n\nVamos configurar seu perfil familiar para obter insights personalizados."
    ]
}


async def start_roadshow(message: Message, state: FSMContext):
    """Start the Silli road-show carousel."""
    locale = get_locale(message.chat.id)
    content = ROADSHOW_CONTENT.get(locale, ROADSHOW_CONTENT["en"])
    
    await state.set_state(Onboarding.roadshow_step)
    await state.update_data(roadshow_step=0, roadshow_content=content)
    
    await show_roadshow_step(message, state)


async def show_roadshow_step(message: Message, state: FSMContext):
    """Show current road-show step with navigation buttons."""
    data = await state.get_data()
    step = data.get("roadshow_step", 0)
    content = data.get("roadshow_content", ROADSHOW_CONTENT["en"])
    
    if step >= len(content):
        # Road-show complete, show family access
        await show_family_access(message, state)
        return
    
    locale = get_locale(message.chat.id)
    
    if locale == "pt_br":
        next_text = "Próximo ▶️"
        skip_text = "Pular ➡️ Acessar Família"
    else:
        next_text = "Next ▶️"
        skip_text = "Skip ➡️ Access Family"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=next_text, callback_data="roadshow:next"),
            InlineKeyboardButton(text=skip_text, callback_data="roadshow:skip")
        ]
    ])
    
    await message.edit_text(content[step], reply_markup=keyboard)


async def show_family_access(message: Message, state: FSMContext):
    """Show family access options after road-show."""
    locale = get_locale(message.chat.id)
    
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
    
    await message.edit_text(text, reply_markup=keyboard)


@router_onboarding.callback_query(F.data == "roadshow:next")
async def handle_roadshow_next(callback: CallbackQuery, state: FSMContext):
    """Handle Next button in road-show."""
    await callback.answer()
    
    data = await state.get_data()
    step = data.get("roadshow_step", 0)
    await state.update_data(roadshow_step=step + 1)
    
    await show_roadshow_step(callback.message, state)


@router_onboarding.callback_query(F.data == "roadshow:skip")
async def handle_roadshow_skip(callback: CallbackQuery, state: FSMContext):
    """Handle Skip button in road-show."""
    await callback.answer()
    await show_family_access(callback.message, state)


@router_onboarding.callback_query(F.data == "family:create")
async def handle_family_create(callback: CallbackQuery, state: FSMContext):
    """Start family creation wizard."""
    await callback.answer()
    
    locale = get_locale(callback.message.chat.id)
    
    if locale == "pt_br":
        text = "Vamos criar sua família! Primeiro, qual é o seu nome?"
        placeholder = "Ex: Maria Silva"
    else:
        text = "Let's create your family! First, what's your name?"
        placeholder = "e.g., Maria Silva"
    
    await state.set_state(Onboarding.parent_name)
    await callback.message.edit_text(text)


@router_onboarding.message(Onboarding.parent_name)
async def handle_parent_name(message: Message, state: FSMContext):
    """Handle parent name input."""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 40:
        locale = get_locale(message.chat.id)
        if locale == "pt_br":
            await message.answer("Nome deve ter entre 2 e 40 caracteres. Tente novamente:")
        else:
            await message.answer("Name must be between 2 and 40 characters. Try again:")
        return
    
    await state.update_data(parent_name=name)
    
    locale = get_locale(message.chat.id)
    if locale == "pt_br":
        text = f"Olá {name}! Você tem um parceiro/a?"
        yes_text = "Sim"
        no_text = "Não"
    else:
        text = f"Hello {name}! Do you have a partner?"
        yes_text = "Yes"
        no_text = "No"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=yes_text, callback_data="partner:yes"),
            InlineKeyboardButton(text=no_text, callback_data="partner:no")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router_onboarding.callback_query(F.data.startswith("partner:"))
async def handle_partner_choice(callback: CallbackQuery, state: FSMContext):
    """Handle partner choice."""
    await callback.answer()
    
    has_partner = callback.data == "partner:yes"
    await state.update_data(has_partner=has_partner)
    
    locale = get_locale(callback.message.chat.id)
    if locale == "pt_br":
        text = "Qual é o nome do seu filho/a?"
    else:
        text = "What's your child's name?"
    
    await state.set_state(Onboarding.child_name)
    await callback.message.edit_text(text)


@router_onboarding.message(Onboarding.child_name)
async def handle_child_name(message: Message, state: FSMContext):
    """Handle child name input."""
    name = message.text.strip()
    
    if len(name) < 2 or len(name) > 40:
        locale = get_locale(message.chat.id)
        if locale == "pt_br":
            await message.answer("Nome deve ter entre 2 e 40 caracteres. Tente novamente:")
        else:
            await message.answer("Name must be between 2 and 40 characters. Try again:")
        return
    
    await state.update_data(child_name=name)
    
    locale = get_locale(message.chat.id)
    if locale == "pt_br":
        text = f"Qual é o sexo de {name}?"
        male_text = "Masculino"
        female_text = "Feminino"
        nb_text = "Não-binário"
    else:
        text = f"What's {name}'s sex?"
        male_text = "Male"
        female_text = "Female"
        nb_text = "Non-binary"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=male_text, callback_data="sex:m"),
            InlineKeyboardButton(text=female_text, callback_data="sex:f"),
            InlineKeyboardButton(text=nb_text, callback_data="sex:nb")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router_onboarding.callback_query(F.data.startswith("sex:"))
async def handle_child_sex(callback: CallbackQuery, state: FSMContext):
    """Handle child sex choice."""
    await callback.answer()
    
    sex = callback.data.split(":")[1]
    await state.update_data(child_sex=sex)
    
    locale = get_locale(callback.message.chat.id)
    if locale == "pt_br":
        text = "Qual é a idade do seu filho/a?"
    else:
        text = "What's your child's age?"
    
    await state.set_state(Onboarding.child_age)
    await callback.message.edit_text(text)


@router_onboarding.message(Onboarding.child_age)
async def handle_child_age(message: Message, state: FSMContext):
    """Handle child age input."""
    try:
        age = int(message.text.strip())
        if age < 0 or age > 17:
            raise ValueError("Age out of range")
    except ValueError:
        locale = get_locale(message.chat.id)
        if locale == "pt_br":
            await message.answer("Idade deve ser um número entre 0 e 17. Tente novamente:")
        else:
            await message.answer("Age must be a number between 0 and 17. Try again:")
        return
    
    await state.update_data(child_age=age)
    
    locale = get_locale(message.chat.id)
    if locale == "pt_br":
        text = "Alguma observação sobre saúde? (opcional, máximo 200 caracteres)"
    else:
        text = "Any health notes? (optional, max 200 characters)"
    
    await state.set_state(Onboarding.health_notes)
    await message.answer(text)


@router_onboarding.message(Onboarding.health_notes)
async def handle_health_notes(message: Message, state: FSMContext):
    """Handle health notes input."""
    notes = message.text.strip()
    
    if len(notes) > 200:
        locale = get_locale(message.chat.id)
        if locale == "pt_br":
            await message.answer("Observações devem ter no máximo 200 caracteres. Tente novamente:")
        else:
            await message.answer("Notes must be 200 characters or less. Try again:")
        return
    
    await state.update_data(health_notes=notes)
    
    locale = get_locale(message.chat.id)
    if locale == "pt_br":
        text = "Quais são os interesses/atividades da família? (ex: esportes, música, leitura)"
    else:
        text = "What are your family's interests/activities? (e.g., sports, music, reading)"
    
    await state.set_state(Onboarding.lifestyle_tags)
    await message.answer(text)


@router_onboarding.message(Onboarding.lifestyle_tags)
async def handle_lifestyle_tags(message: Message, state: FSMContext):
    """Handle lifestyle tags input."""
    tags = message.text.strip()
    await state.update_data(lifestyle_tags=tags)
    
    locale = get_locale(message.chat.id)
    if locale == "pt_br":
        text = "Você tem outros filhos?"
        yes_text = "Sim"
        done_text = "Não, terminamos"
    else:
        text = "Do you have other children?"
        yes_text = "Yes"
        done_text = "No, we're done"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=yes_text, callback_data="other_children:yes"),
            InlineKeyboardButton(text=done_text, callback_data="other_children:done")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@router_onboarding.callback_query(F.data.startswith("other_children:"))
async def handle_other_children(callback: CallbackQuery, state: FSMContext):
    """Handle other children choice."""
    await callback.answer()
    
    if callback.data == "other_children:yes":
        # Loop back to child name for additional children
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            text = "Qual é o nome do próximo filho/a?"
        else:
            text = "What's the next child's name?"
        
        await state.set_state(Onboarding.child_name)
        await callback.message.edit_text(text)
    else:
        # Move to pets question
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            text = "Você tem animais de estimação?"
            yes_text = "Sim"
            no_text = "Não"
        else:
            text = "Do you have pets?"
            yes_text = "Yes"
            no_text = "No"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=yes_text, callback_data="pets:yes"),
                InlineKeyboardButton(text=no_text, callback_data="pets:no")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)


@router_onboarding.callback_query(F.data.startswith("pets:"))
async def handle_pets_choice(callback: CallbackQuery, state: FSMContext):
    """Handle pets choice and complete family creation."""
    await callback.answer()
    
    has_pets = callback.data == "pets:yes"
    await state.update_data(has_pets=has_pets)
    
    # Complete family creation
    await complete_family_creation(callback.message, state)


async def complete_family_creation(message: Message, state: FSMContext):
    """Complete the family creation process."""
    data = await state.get_data()
    
    # Generate family ID
    family_id = f"fam_{message.chat.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create family profile
    family_data = {
        "family_id": family_id,
        "parent_name": data.get("parent_name"),
        "has_partner": data.get("has_partner", False),
        "children": [{
            "name": data.get("child_name"),
            "sex": data.get("child_sex"),
            "age": data.get("child_age"),
            "health_notes": data.get("health_notes", "")
        }],
        "lifestyle_tags": data.get("lifestyle_tags", ""),
        "has_pets": data.get("has_pets", False),
        "enabled_dyads": set(),  # Empty set for now
        "created_at": datetime.now().isoformat()
    }
    
    # Save family profile
    from .families import families
    families.save_family(family_data)
    
    # Update user profile to link to family
    profiles.upsert_fields_sync(message.chat.id, {
        "family_id": family_id,
        "status": "active"
    })
    
    # Clear FSM state
    await state.clear()
    
    locale = get_locale(message.chat.id)
    if locale == "pt_br":
        text = f"✅ Família criada com sucesso!\n\nID da Família: `{family_id}`\n\nAgora vamos configurar os Dyads disponíveis."
    else:
        text = f"✅ Family created successfully!\n\nFamily ID: `{family_id}`\n\nNow let's set up available Dyads."
    
    await message.edit_text(text)
    
    # Show Dyad selection
    await show_dyad_selection(message)


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


@router_onboarding.callback_query(F.data.startswith("dyad:"))
async def handle_dyad_selection(callback: CallbackQuery):
    """Handle Dyad selection."""
    await callback.answer()
    
    if callback.data == "dyad:continue":
        # Complete onboarding
        locale = get_locale(callback.message.chat.id)
        if locale == "pt_br":
            text = "🎉 Parabéns! Seu perfil está configurado.\n\nUse /help para ver todos os comandos disponíveis."
        else:
            text = "🎉 Congratulations! Your profile is set up.\n\nUse /help to see all available commands."
        
        await callback.message.edit_text(text)
    else:
        # Toggle Dyad selection
        dyad_id = callback.data.split(":")[1]
        # TODO: Implement Dyad toggling logic
        await callback.answer(f"Dyad {dyad_id} toggled")
