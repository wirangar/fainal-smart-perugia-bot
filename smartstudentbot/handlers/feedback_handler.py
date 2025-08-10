from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from utils.i18n import get_text
from handlers.cmd_start import UserState
from utils.db_utils import add_feedback

router = Router()

# --- FSM States for Feedback ---
class FeedbackForm(StatesGroup):
    getting_rating = State()
    getting_comment = State()

# --- Command Handler ---
@router.message(Command("feedback"))
async def cmd_feedback(message: types.Message, state: FSMContext):
    """Starts the feedback process."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    # Create rating buttons (1-5 stars)
    buttons = [InlineKeyboardButton(text=f"{'⭐'*i}", callback_data=f"feedback_rating_{i}") for i in range(1, 6)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])

    await message.answer(get_text("feedback_intro", lang), reply_markup=keyboard)
    await state.set_state(FeedbackForm.getting_rating)

# --- Callback and FSM Handlers ---
@router.callback_query(FeedbackForm.getting_rating, F.data.startswith("feedback_rating_"))
async def process_rating(callback_query: types.CallbackQuery, state: FSMContext):
    """Processes the star rating and asks for an optional comment."""
    rating = int(callback_query.data.split("_")[-1])
    await state.update_data(rating=rating)

    lang = (await state.get_data()).get(UserState.language, "en")

    # Ask for comment with a skip button
    skip_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="/skip", callback_data="feedback_skip_comment")]
    ])

    await callback_query.message.edit_text(get_text("feedback_ask_comment", lang), reply_markup=skip_button)
    await state.set_state(FeedbackForm.getting_comment)
    await callback_query.answer()

@router.callback_query(FeedbackForm.getting_comment, F.data == "feedback_skip_comment")
async def process_skip_comment(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handles skipping the comment, saves only the rating."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    await add_feedback(session, {
        "user_id": callback_query.from_user.id,
        "rating": user_data.get("rating"),
        "text": None
    })

    await callback_query.message.edit_text(get_text("feedback_skip_comment", lang))
    await state.clear()
    await callback_query.answer()

@router.message(FeedbackForm.getting_comment)
async def process_comment(message: types.Message, state: FSMContext, session: AsyncSession):
    """Processes the text comment and saves everything."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    await add_feedback(session, {
        "user_id": message.from_user.id,
        "rating": user_data.get("rating"),
        "text": message.text
    })

    await message.answer(get_text("feedback_thanks", lang))
    await state.clear()
