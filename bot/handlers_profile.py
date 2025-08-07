from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from bot.profiles import profiles
from loguru import logger
import os

router_profile = Router()

@router_profile.message(Command("profile"))
async def profile_command(message: Message):
    chat_id = message.chat.id
    profile = await profiles.get_profile_by_chat(chat_id)
    if not profile:
        await message.reply("No profile found. Please run /onboard to set up your family profile.")
        return
    # Compact summary
    parent = f"{profile.parent_name} ({profile.parent_age if profile.parent_age else '—'})"
    tz = profile.timezone
    children = profile.children or []
    children_lines = [f"• {c.name}, {c.age_years}y, {c.sex}" for c in children]
    notes = (profile.health_notes or "")[:120]
    members = len(profile.members)
    summary = (
        f"Parent: {parent}, TZ: {tz}\n"
        f"Children:\n" + ("\n".join(children_lines) if children_lines else "—") + "\n"
        f"Notes: {notes if notes else '—'}\n"
        f"Members: {members}"
    )
    await message.reply(summary)

@router_profile.message(Command("reason_on"))
async def reason_on_command(message: Message):
    """Enable cloud reasoning for the family"""
    chat_id = message.chat.id
    profile = await profiles.get_profile_by_chat(chat_id)
    
    if not profile:
        await message.reply("No profile found. Please run /onboard to set up your family profile.")
        return
    
    if not profile.complete:
        await message.reply("You need a complete profile to enable cloud reasoning. Run /onboard first.")
        return
    
    # Update profile to enable cloud reasoning
    updated_profile = await profiles.upsert_fields(profile.family_id, cloud_reasoning=True)
    
    await message.reply(
        "✅ Cloud reasoning enabled for your family!\n\n"
        "Your family will now receive AI-powered tips and insights. "
        "Use /reason_status to check the current status."
    )

@router_profile.message(Command("reason_off"))
async def reason_off_command(message: Message):
    """Disable cloud reasoning for the family"""
    chat_id = message.chat.id
    profile = await profiles.get_profile_by_chat(chat_id)
    
    if not profile:
        await message.reply("No profile found. Please run /onboard to set up your family profile.")
        return
    
    if not profile.complete:
        await message.reply("You need a complete profile to disable cloud reasoning. Run /onboard first.")
        return
    
    # Update profile to disable cloud reasoning
    updated_profile = await profiles.upsert_fields(profile.family_id, cloud_reasoning=False)
    
    await message.reply(
        "❌ Cloud reasoning disabled for your family.\n\n"
        "Your family will no longer receive AI-powered tips and insights. "
        "Use /reason_on to re-enable when ready."
    )

@router_profile.message(Command("reason_status"))
async def reason_status_command(message: Message):
    """Show cloud reasoning status for the family"""
    chat_id = message.chat.id
    profile = await profiles.get_profile_by_chat(chat_id)
    
    if not profile:
        await message.reply("No profile found. Please run /onboard to set up your family profile.")
        return
    
    if not profile.complete:
        await message.reply("You need a complete profile to check reasoning status. Run /onboard first.")
        return
    
    # Check global and family settings
    global_enabled = os.getenv('REASONER_ENABLED', '0').lower() in ('1', 'true', 'yes')
    family_enabled = profile.cloud_reasoning
    model_hint = os.getenv('REASONER_MODEL_HINT', 'gpt-oss-20b')
    
    # Determine effective status
    effective_enabled = global_enabled and family_enabled
    
    status_lines = []
    status_lines.append("🤖 **Cloud Reasoning Status**")
    status_lines.append("")
    
    if effective_enabled:
        status_lines.append("✅ **ENABLED** - Your family receives AI-powered insights")
    else:
        status_lines.append("❌ **DISABLED** - Your family uses basic responses")
    
    status_lines.append("")
    status_lines.append("**Settings:**")
    status_lines.append(f"• Global service: {'✅ ON' if global_enabled else '❌ OFF'}")
    status_lines.append(f"• Family setting: {'✅ ON' if family_enabled else '❌ OFF'}")
    status_lines.append(f"• Model: {model_hint}")
    
    status_lines.append("")
    if effective_enabled:
        status_lines.append("💡 **Commands:**")
        status_lines.append("• /reason_off - Disable for your family")
    else:
        status_lines.append("💡 **Commands:**")
        if not global_enabled:
            status_lines.append("• Global service is disabled (contact admin)")
        elif not family_enabled:
            status_lines.append("• /reason_on - Enable for your family")
    
    await message.reply("\n".join(status_lines))

@router_profile.message(Command("invite"))
async def invite_command(message: Message):
    chat_id = message.chat.id
    profile = await profiles.get_profile_by_chat(chat_id)
    if not profile or not profile.complete:
        await message.reply("You need a complete profile to invite family. Run /onboard first.")
        return
    code = await profiles.generate_join_code(profile.family_id)
    await message.reply(
        f"Share this code with a family member in Telegram:\n/join {code} (expires in 48h)."
    )

@router_profile.message(Command("join"))
async def join_command(message: Message, command: CommandObject):
    chat_id = message.chat.id
    code = None
    if command.args:
        code = command.args.strip().split()[0]
    if not code:
        await message.reply("Usage: /join <CODE>\nAsk a family member to send you an invite code via /invite.")
        return
    try:
        profile = await profiles.consume_join_code(code, chat_id)
        await message.reply(f"Joined family {profile.family_id}. You are now a member.")
    except Exception as e:
        logger.warning(f"Join failed: {e}")
        await message.reply("Invalid or expired code. Ask your family to send a new invite via /invite.")