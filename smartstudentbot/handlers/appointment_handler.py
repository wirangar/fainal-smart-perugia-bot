from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.i18n import get_text
from handlers.cmd_start import UserState
from models_db import AppointmentStatus, User
from utils.db_utils import create_appointment, update_appointment_status, get_or_create_user
from config import ADMIN_CHAT_IDS

router = Router()

# --- FSM States for Appointment Booking ---
class AppointmentForm(StatesGroup):
    getting_topic = State()
    getting_time = State()

# --- Command Handler ---
@router.message(Command("appointment"))
async def cmd_appointment_start(message: types.Message, state: FSMContext, session: AsyncSession):
    """Starts the appointment booking process."""
    # Ensure user exists in DB
    await get_or_create_user(session, {"user_id": message.from_user.id, "first_name": message.from_user.first_name, "username": message.from_user.username})
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("appointment_intro", lang))
    await state.set_state(AppointmentForm.getting_topic)

# --- FSM Handlers ---
@router.message(AppointmentForm.getting_topic)
async def process_appointment_topic(message: types.Message, state: FSMContext):
    """Processes the appointment topic and asks for the time."""
    await state.update_data(topic=message.text)
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("appointment_ask_time", lang))
    await state.set_state(AppointmentForm.getting_time)

@router.message(AppointmentForm.getting_time)
async def process_appointment_time(message: types.Message, state: FSMContext, session: AsyncSession):
    """Processes the time, saves the request, and notifies admins."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    appointment_data = {
        "user_id": message.from_user.id,
        "topic": user_data.get("topic"),
        "preferred_datetime": message.text
    }

    appointment = await create_appointment(session, appointment_data)

    # Notify Admins
    admin_text = get_text("admin_appointment_request", "en").format(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name,
        topic=appointment.topic,
        time=appointment.preferred_datetime
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=get_text("admin_appointment_confirm_button", "en"), callback_data=f"appt_confirm_{appointment.id}"),
        InlineKeyboardButton(text=get_text("admin_appointment_cancel_button", "en"), callback_data=f"appt_cancel_{appointment.id}")
    ]])
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await message.bot.send_message(admin_id, admin_text, reply_markup=keyboard)
        except Exception as e:
            print(f"Failed to send appointment alert to admin {admin_id}: {e}")

    await message.answer(get_text("appointment_thanks", lang))
    await state.clear()

# --- Admin Callback Handler ---
# Note: In a larger app, this might be moved to admin_handler.py
@router.callback_query(F.data.startswith("appt_confirm_") | F.data.startswith("appt_cancel_"))
async def handle_appointment_confirmation(callback_query: types.CallbackQuery, session: AsyncSession):
    """Handles admin confirming or cancelling an appointment."""
    action, appt_id_str = callback_query.data.split("_", 1)
    appointment_id = int(appt_id_str)
    admin_id = callback_query.from_user.id

    new_status = AppointmentStatus.CONFIRMED if action == "appt_confirm" else AppointmentStatus.CANCELLED

    appointment = await update_appointment_status(session, appointment_id, new_status, admin_id)

    if not appointment:
        await callback_query.answer("Appointment not found.", show_alert=True)
        return

    # Get user's language to send them a message in their language
    stmt = select(User.language_code).where(User.user_id == appointment.user_id)
    result = await session.execute(stmt)
    user_lang = result.scalar_one_or_none() or "en"

    if new_status == AppointmentStatus.CONFIRMED:
        await callback_query.message.edit_text(get_text("admin_appointment_confirmed", "en").format(appointment_id=appointment.id))
        await callback_query.bot.send_message(
            appointment.user_id,
            get_text("user_appointment_confirmed", user_lang).format(topic=appointment.topic)
        )
    else:
        await callback_query.message.edit_text(get_text("admin_appointment_cancelled", "en").format(appointment_id=appointment.id))
        await callback_query.bot.send_message(
            appointment.user_id,
            get_text("user_appointment_cancelled", user_lang).format(topic=appointment.topic)
        )

    await callback_query.answer()
