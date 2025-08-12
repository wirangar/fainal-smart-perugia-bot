from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from utils.i18n import get_text
from handlers.cmd_start import UserState
from models_db import EventType, EventStatus
from utils.db_utils import create_event, add_document
from config import ADMIN_CHAT_IDS

router = Router()

# --- FSM States for Consultation Form ---
class ConsultForm(StatesGroup):
    getting_field = State()
    getting_gpa = State()
    getting_budget = State()
    getting_language = State()
    getting_resume = State()

# --- Command Handler ---
@router.message(Command("consult"))
async def cmd_consult_start(message: types.Message, state: FSMContext):
    """Starts the consultation form."""
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("consult_intro", lang))
    await message.answer(get_text("consult_ask_field", lang))
    await state.set_state(ConsultForm.getting_field)

# --- FSM Handlers ---
@router.message(ConsultForm.getting_field)
async def process_consult_field(message: types.Message, state: FSMContext):
    await state.update_data(field=message.text)
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("consult_ask_gpa", lang))
    await state.set_state(ConsultForm.getting_gpa)

@router.message(ConsultForm.getting_gpa)
async def process_consult_gpa(message: types.Message, state: FSMContext):
    await state.update_data(gpa=message.text)
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("consult_ask_budget", lang))
    await state.set_state(ConsultForm.getting_budget)

@router.message(ConsultForm.getting_budget)
async def process_consult_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=message.text)
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("consult_ask_language", lang))
    await state.set_state(ConsultForm.getting_language)

@router.message(ConsultForm.getting_language)
async def process_consult_language(message: types.Message, state: FSMContext):
    await state.update_data(language_level=message.text)
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("consult_ask_resume", lang))
    await state.set_state(ConsultForm.getting_resume)

@router.message(ConsultForm.getting_resume, F.document)
async def process_consult_resume(message: types.Message, state: FSMContext, session: AsyncSession):
    """Processes the resume, saves it, and creates a consultation appointment."""
    lang = (await state.get_data()).get(UserState.language, "en")

    if message.document.mime_type != "application/pdf":
        await message.answer(get_text("consult_invalid_pdf", lang))
        return

    # Save the document
    doc = await add_document(session, {
        "user_id": message.from_user.id,
        "file_id": message.document.file_id,
        "file_unique_id": message.document.file_unique_id,
        "file_name": message.document.file_name,
        "file_type": message.document.mime_type,
        "category": "consultation_resume"
    })

    # Create a summary of the consultation request
    user_data = await state.get_data()
    consultation_details = (
        f"Field: {user_data.get('field')}\n"
        f"GPA: {user_data.get('gpa')}\n"
        f"Budget: {user_data.get('budget')}\n"
        f"Language: {user_data.get('language_level')}\n"
        f"Resume saved with doc ID: {doc.id}"
    )

    # Create a PENDING appointment/event for this consultation
    event_data = {
        "title": f"Consultation Request for {message.from_user.full_name}",
        "description": consultation_details,
        "event_type": EventType.APPOINTMENT,
        "event_datetime": datetime.utcnow(), # Placeholder, admin will set the real time
        "status": EventStatus.PENDING,
        "created_by": message.from_user.id
    }

    await create_event(session, event_data)

    # Notify user and clear state
    await message.answer(get_text("consult_thanks", lang))
    await state.clear()

    # Notify admins (optional, since it's now an event to be managed)
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await message.bot.send_message(admin_id, f"New consultation request received from user {message.from_user.id}. Check the events panel to manage it.")
        except Exception as e:
            print(f"Failed to send consult alert to admin {admin_id}: {e}")
