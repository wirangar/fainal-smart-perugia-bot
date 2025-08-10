import re
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from utils.i18n import get_text
from handlers.cmd_start import UserState
from utils.db_utils import get_or_create_user, get_roommate_profile, create_or_update_roommate_profile, get_active_roommate_profiles

router = Router()

# --- FSM States for Profile Creation ---
class RoommateForm(StatesGroup):
    getting_budget = State()
    getting_locations = State()
    getting_habits = State()
    getting_about = State()

# --- Helper Functions ---
async def get_roommate_menu(session: AsyncSession, user_id: int, lang: str):
    profile = await get_roommate_profile(session, user_id)
    text = get_text("roommate_menu_intro", lang)

    buttons = [
        [InlineKeyboardButton(text=get_text("roommate_button_create_profile", lang), callback_data="roommate_create_profile")],
        [InlineKeyboardButton(text=get_text("roommate_button_search", lang), callback_data="roommate_search")]
    ]
    if profile:
        toggle_text_key = "roommate_button_toggle_inactive" if profile.is_active else "roommate_button_toggle_active"
        toggle_action = "deactivate" if profile.is_active else "activate"
        buttons.append([InlineKeyboardButton(text=get_text(toggle_text_key, lang), callback_data=f"roommate_toggle_{toggle_action}")])

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Command and Menu Handlers ---
@router.message(Command("roommate"))
async def cmd_roommate(message: types.Message, state: FSMContext, session: AsyncSession):
    """Displays the main roommate finder menu."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")
    await get_or_create_user(session, {"user_id": message.from_user.id, "first_name": message.from_user.first_name, "username": message.from_user.username, "language_code": lang})
    text, markup = await get_roommate_menu(session, message.from_user.id, lang)
    await message.answer(text, reply_markup=markup)

# --- Callback Handlers for Menu Actions ---
@router.callback_query(F.data == "roommate_create_profile")
async def start_profile_form(callback_query: types.CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get(UserState.language, "en")
    await callback_query.message.answer(get_text("roommate_form_ask_budget", lang))
    await state.set_state(RoommateForm.getting_budget)
    await callback_query.answer()

@router.callback_query(F.data == "roommate_search")
async def search_for_roommates(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    lang = (await state.get_data()).get(UserState.language, "en")
    profiles = await get_active_roommate_profiles(session, callback_query.from_user.id)

    if not profiles:
        await callback_query.message.answer(get_text("roommate_search_none_found", lang))
    else:
        await callback_query.message.answer(get_text("roommate_search_results_title", lang))
        for profile in profiles:
            user = await get_or_create_user(session, {"user_id": profile.user_id, "first_name": "User"})
            card = get_text("roommate_profile_card", lang).format(
                first_name=user.first_name,
                budget_min=profile.budget_min, budget_max=profile.budget_max,
                locations=profile.location_preferences, habits=profile.habits,
                about_me=profile.about_me
            )
            contact_button = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Contact {user.first_name}", url=f"tg://user?id={profile.user_id}")]
            ])
            await callback_query.message.answer(card, reply_markup=contact_button)
    await callback_query.answer()

@router.callback_query(F.data.startswith("roommate_toggle_"))
async def toggle_profile_activity(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    action = callback_query.data.split("_")[-1]
    is_active = (action == "activate")
    lang = (await state.get_data()).get(UserState.language, "en")

    await create_or_update_roommate_profile(session, callback_query.from_user.id, {"is_active": is_active})

    text_key = "roommate_profile_active" if is_active else "roommate_profile_inactive"
    await callback_query.answer(get_text(text_key, lang), show_alert=True)

    text, markup = await get_roommate_menu(session, callback_query.from_user.id, lang)
    await callback_query.message.edit_text(text, reply_markup=markup)

# --- FSM Handlers for Profile Creation ---
@router.message(RoommateForm.getting_budget)
async def process_budget(message: types.Message, state: FSMContext):
    lang = (await state.get_data()).get(UserState.language, "en")
    match = re.match(r'(\d+)\s*-\s*(\d+)', message.text)
    if match:
        await state.update_data(budget_min=int(match.group(1)), budget_max=int(match.group(2)))
        await message.answer(get_text("roommate_form_ask_locations", lang))
        await state.set_state(RoommateForm.getting_locations)
    else:
        await message.answer(get_text("isee_invalid_input", lang))

@router.message(RoommateForm.getting_locations)
async def process_locations(message: types.Message, state: FSMContext):
    lang = (await state.get_data()).get(UserState.language, "en")
    await state.update_data(location_preferences=message.text)
    await message.answer(get_text("roommate_form_ask_habits", lang))
    await state.set_state(RoommateForm.getting_habits)

@router.message(RoommateForm.getting_habits)
async def process_habits(message: types.Message, state: FSMContext):
    lang = (await state.get_data()).get(UserState.language, "en")
    await state.update_data(habits=message.text)
    await message.answer(get_text("roommate_form_ask_about", lang))
    await state.set_state(RoommateForm.getting_about)

@router.message(RoommateForm.getting_about)
async def process_about(message: types.Message, state: FSMContext, session: AsyncSession):
    lang = (await state.get_data()).get(UserState.language, "en")
    await state.update_data(about_me=message.text)

    profile_data = await state.get_data()
    profile_data.pop(UserState.language, None)

    # Check if this is the first time they are creating the profile to award points
    existing_profile = await get_roommate_profile(session, message.from_user.id)
    is_first_creation = not existing_profile or not existing_profile.about_me

    await create_or_update_roommate_profile(session, message.from_user.id, profile_data)

    if is_first_creation:
        from utils.gamification_utils import award_points, PointsAction, grant_achievement, Achievement
        await award_points(session, message.from_user.id, PointsAction.COMPLETE_PROFILE)
        await grant_achievement(session, message.from_user.id, Achievement.FIRST_STEPS)

    await message.answer(get_text("roommate_form_complete", lang))
    await state.clear()

    text, markup = await get_roommate_menu(session, message.from_user.id, lang)
    await message.answer(text, reply_markup=markup)
