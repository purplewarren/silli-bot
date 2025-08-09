from aiogram import Router, types
from aiogram.filters import Command
from bot.reason_client import client

router_reason_debug = Router(name="reason_debug")

@router_reason_debug.message(Command("reason_debug"))
async def reason_debug(message: types.Message):
    from bot.admin import is_admin
    
    # Check admin access
    if not is_admin(message.from_user.id):
        await message.answer("Command not available.", parse_mode="HTML")
        return
    
    st = client.status()
    await message.answer(
        "<b>ME Status</b>\n"
        f"hint: {st.get('model_hint','?')}\n"
        f"used: {st.get('model_used','?')}\n"
        f"fallback: {st.get('allow_fallback','?')}\n"
        f"cache: {st.get('cache',{})}\n",
        parse_mode="HTML"
    )
