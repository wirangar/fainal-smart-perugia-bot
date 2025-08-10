from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from utils.i18n import get_text
from handlers.cmd_start import UserState
from models_db import StoryStatus
from utils.db_utils import get_or_create_user, add_success_story, get_random_approved_story
from config import ADMIN_CHAT_IDS

router = Router()

# --- FSM States for Story Submission ---
class StoryForm(StatesGroup):
    getting_story = State()

# --- Command Handler ---
@router.message(Command("success_story"))
async def cmd_success_story(message: types.Message, state: FSMContext):
    """Displays the success story menu."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("success_story_button_share", lang), callback_data="story_share")],
        [InlineKeyboardButton(text=get_text("success_story_button_read", lang), callback_data="story_read")]
    ])

    await message.answer(get_text("success_story_menu", lang), reply_markup=keyboard)

# --- Callback Handlers ---
@router.callback_query(F.data == "story_share")
async def start_sharing_story(callback_query: types.CallbackQuery, state: FSMContext):
    """Starts the FSM for sharing a story."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    await callback_query.message.answer(get_text("success_story_share_start", lang))
    await state.set_state(StoryForm.getting_story)
    await callback_query.answer()

@router.callback_query(F.data == "story_read")
async def read_story(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Fetches and displays a random approved success story."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    story = await get_random_approved_story(session)

    if not story:
        await callback_query.message.answer(get_text("success_story_read_none", lang))
    else:
        await callback_query.message.answer(get_text("success_story_from_user", lang))
        # Determine the media type and send accordingly
        if story.media_type == "photo":
            await callback_query.message.answer_photo(story.media_id, caption=story.story_text)
        elif story.media_type == "video":
            await callback_query.message.answer_video(story.media_id, caption=story.story_text)
        else:
            await callback_query.message.answer(story.story_text)

    await callback_query.answer()

# --- FSM Message Handler ---
@router.message(StoryForm.getting_story)
async def process_story_submission(message: types.Message, state: FSMContext, session: AsyncSession):
    """Receives the user's story, saves it to the DB, and notifies admins."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    db_user = await get_or_create_user(session, {
        "user_id": message.from_user.id, "username": message.from_user.username,
        "first_name": message.from_user.first_name, "language_code": lang
    })

    story_text = message.text or message.caption
    if not story_text:
        await message.answer("Please provide some text for your story.")
        return

    media_id, media_type = (message.photo[-1].file_id, "photo") if message.photo else \
                           (message.video.file_id, "video") if message.video else (None, None)

    story = await add_success_story(session, {
        "user_id": db_user.user_id, "story_text": story_text,
        "media_id": media_id, "media_type": media_type
    })

    # Notify Admins
    approval_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text("admin_approve_story_button", "en"), callback_data=f"story_approve_{story.id}"),
            InlineKeyboardButton(text=get_text("admin_reject_story_button", "en"), callback_data=f"story_reject_{story.id}")
        ]
    ])
    admin_text = get_text("admin_approve_story_prompt", "en").format(story_text=story.story_text[:800])
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text, reply_markup=approval_keyboard)
        except Exception as e:
            print(f"Failed to send story approval to admin {admin_id}: {e}")

    # Award points for sharing
    from utils.gamification_utils import award_points, PointsAction, grant_achievement, Achievement
    await award_points(session, db_user.user_id, PointsAction.SHARE_SUCCESS_STORY)
    await grant_achievement(session, db_user.user_id, Achievement.STORY_TELLER)

    await message.answer(get_text("success_story_share_thanks", lang))
    await state.clear()
