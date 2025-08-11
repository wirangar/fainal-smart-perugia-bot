from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from utils.i18n import get_text
from handlers.cmd_start import UserState
from models_db import Event, EventType, EventStatus, User
from utils.db_utils import create_event, get_upcoming_events, register_user_for_event
from config import ADMIN_CHAT_IDS

router = Router()

# --- FSM States for Appointment Booking ---
class AppointmentForm(StatesGroup):
    getting_topic = State()
    getting_time = State()

# --- User-facing Commands ---
@router.message(Command("events"))
async def cmd_events(message: types.Message, state: FSMContext, session: AsyncSession):
    """Displays a list of upcoming events."""
    lang = (await state.get_data()).get(UserState.language, "en")
    events = await get_upcoming_events(session)

    if not events:
        await message.answer(get_text("events_none", lang))
        return

    await message.answer(get_text("events_intro", lang))
    for event in events:
        event_time_str = event.event_datetime.strftime("%Y-%m-%d %H:%M")
        card = get_text("event_card", lang).format(
            title=event.title, description=event.description,
            datetime=event_time_str, location=event.location
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("event_register_button", lang), callback_data=f"event_register_{event.id}")]
        ])
        await message.answer(card, reply_markup=markup, parse_mode="Markdown")

@router.message(Command("appointment"))
async def cmd_appointment_start(message: types.Message, state: FSMContext):
    """Starts the private appointment booking process."""
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("appointment_intro", lang))
    await state.set_state(AppointmentForm.getting_topic)

# --- FSM Handlers for Appointment ---
@router.message(AppointmentForm.getting_topic)
async def process_appointment_topic(message: types.Message, state: FSMContext):
    await state.update_data(topic=message.text)
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("appointment_ask_time", lang))
    await state.set_state(AppointmentForm.getting_time)

@router.message(AppointmentForm.getting_time)
async def process_appointment_time(message: types.Message, state: FSMContext, session: AsyncSession):
    """Processes the time and creates a PENDING appointment event."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    # This is a crude way to parse time, a real bot would use a calendar or more robust parsing
    try:
        # For simplicity, we just store the user's text and assume a future date
        event_datetime = datetime.now()
    except Exception:
        event_datetime = datetime.now()

    event_data = {
        "title": f"Appointment: {user_data.get('topic')}",
        "description": f"Requested by user {message.from_user.id}. Preferred time: {message.text}",
        "event_type": EventType.APPOINTMENT,
        "event_datetime": event_datetime, # Placeholder datetime
        "status": EventStatus.PENDING,
        "created_by": message.from_user.id
    }

    event = await create_event(session, event_data)

    # Admin notification logic would go here, similar to before

    await message.answer(get_text("appointment_thanks", lang))
    await state.clear()

# --- Callback Handlers for Public Events ---
@router.callback_query(F.data.startswith("event_register_"))
async def register_for_event(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handles a user clicking the 'Register' button for an event."""
    event_id = int(callback_query.data.split("_")[-1])
    user_id = callback_query.from_user.id
    lang = (await state.get_data()).get(UserState.language, "en")

    success, reason = await register_user_for_event(session, user_id, event_id)

    if success:
        event = (await session.execute(select(Event).where(Event.id == event_id))).scalar_one()
        await callback_query.answer(get_text("event_registration_success", lang).format(title=event.title), show_alert=True)
    else:
        key = f"event_registration_{reason}"
        event = (await session.execute(select(Event).where(Event.id == event_id))).scalar_one()
        await callback_query.answer(get_text(key, lang).format(title=event.title), show_alert=True)
