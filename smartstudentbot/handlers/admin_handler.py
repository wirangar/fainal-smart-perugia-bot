from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from config import ADMIN_CHAT_IDS
from utils.i18n import get_text
from handlers.live_chat_handler import LiveChat, chat_connections
from handlers.cmd_start import UserState

router = Router()

# Only admins can use the features in this handler
router.message.filter(F.from_user.id.in_(ADMIN_CHAT_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_CHAT_IDS))


@router.callback_query(F.data.startswith("accept_chat_"))
async def accept_chat(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles an admin accepting a live chat request."""
    user_id_to_connect = int(callback_query.data.split("_")[-1])
    admin_id = callback_query.from_user.id

    # Get the user's state to see if they are still waiting
    user_state = FSMContext(
        storage=state.storage,
        key=state.key.with_user_id(user_id_to_connect)
    )

    if await user_state.get_state() != LiveChat.waiting_for_admin:
        await callback_query.answer("User is no longer waiting.", show_alert=True)
        await callback_query.message.delete() # Clean up the admin message
        return

    # Connect the admin and user
    await state.set_state(LiveChat.in_chat_with_admin)
    await user_state.set_state(LiveChat.in_chat_with_admin)

    chat_connections[admin_id] = user_id_to_connect
    chat_connections[user_id_to_connect] = admin_id

    # Notify both parties
    await callback_query.answer("You are connected.")
    await callback_query.message.edit_text(f"You have accepted the chat with user {user_id_to_connect}.")

    # Get user's language to send them a message in their language
    user_fsm_data = await user_state.get_data()
    user_lang = user_fsm_data.get(UserState.language, "en")

    await callback_query.bot.send_message(
        user_id_to_connect,
        get_text("live_chat_connected_user", user_lang)
    )
    await callback_query.bot.send_message(
        admin_id,
        get_text("live_chat_connected_admin", "en") # Assume admin lang is en
    )

@router.message(LiveChat.in_chat_with_admin)
async def forward_message_to_user(message: types.Message, state: FSMContext):
    """Forwards an admin's message to the connected user."""
    user_id = chat_connections.get(message.from_user.id)
    if not user_id:
        # Should not happen, but as a safeguard
        await state.clear()
        return

    if message.text:
        await message.bot.send_message(user_id, f"Admin: {message.text}")
    else:
        await message.copy_to(user_id)


@router.callback_query(F.data.startswith("story_approve_") | F.data.startswith("story_reject_"))
async def approve_reject_story(callback_query: types.CallbackQuery, session: AsyncSession):
    """Handles an admin approving or rejecting a success story."""
    action, story_id_str = callback_query.data.rsplit("_", 1)
    story_id = int(story_id_str)

    from models_db import StoryStatus
    from utils.db_utils import update_story_status

    new_status = StoryStatus.APPROVED if action == "story_approve" else StoryStatus.REJECTED

    story = await update_story_status(session, story_id, new_status)

    if not story:
        await callback_query.answer("Story not found.", show_alert=True)
        return

    if new_status == StoryStatus.APPROVED:
        await callback_query.message.edit_text(get_text("admin_story_approved", "en").format(story_id=story.id))
    else:
        await callback_query.message.edit_text(get_text("admin_story_rejected", "en").format(story_id=story.id))

    await callback_query.answer()
