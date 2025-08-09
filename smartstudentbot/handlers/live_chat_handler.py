from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.i18n import get_text
from handlers.cmd_start import UserState
# The alert_admin function will be created in the next step
# from utils.alert_admin import alert_admins_for_chat

router = Router()

# --- FSM States for Live Chat ---
class LiveChat(StatesGroup):
    waiting_for_admin = State()
    in_chat_with_admin = State()

# This dictionary will act as a temporary "database" to link users and admins
# In a real application, this should be in Redis or a proper database.
chat_connections = {} # {user_id: admin_id, admin_id: user_id}

@router.message(Command("live_chat"))
async def cmd_live_chat(message: types.Message, state: FSMContext):
    """Initiates a live chat request from a user."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    await state.set_state(LiveChat.waiting_for_admin)
    await message.answer(get_text("live_chat_start", lang))

    # --- Admin Notification ---
    # This function will send a message to all admins.
    from utils.alert_admin import alert_admins_for_chat
    await alert_admins_for_chat(message.bot, message.from_user.id, message.from_user.full_name)


@router.message(Command("end_chat"))
async def cmd_end_chat(message: types.Message, state: FSMContext):
    """Ends a chat session, can be initiated by user or admin."""
    current_state = await state.get_state()
    if current_state not in [LiveChat.waiting_for_admin, LiveChat.in_chat_with_admin]:
        return # Ignore if not in a chat state

    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    # Find the other person in the chat
    partner_id = chat_connections.pop(message.from_user.id, None)
    if partner_id:
        chat_connections.pop(partner_id, None)
        # We need the bot instance to send a message to the other user
        # This shows a limitation of this simple approach. We'll address this.
        try:
            await message.bot.send_message(partner_id, get_text("live_chat_ended_by_user", "en")) # Assume admin lang is en
        except Exception as e:
            print(f"Could not notify partner {partner_id} of chat end: {e}")

    await state.clear()
    await message.answer(get_text("live_chat_self_ended", lang))


@router.message(LiveChat.in_chat_with_admin)
async def forward_message_to_admin(message: types.Message, state: FSMContext):
    """Forwards a user's message to the connected admin."""
    admin_id = chat_connections.get(message.from_user.id)
    if not admin_id:
        # This case shouldn't happen if state is managed correctly
        await cmd_end_chat(message, state)
        return

    # Forward the message content to the admin
    # A simple forward might reveal the user's identity, so we copy it instead.
    if message.text:
        await message.bot.send_message(admin_id, f"User: {message.text}")
    else:
        # For non-text messages, you might want to forward or send a notification
        await message.copy_to(admin_id)
