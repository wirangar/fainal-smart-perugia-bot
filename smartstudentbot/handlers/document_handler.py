import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from utils.i18n import get_text
from handlers.cmd_start import UserState
from utils.db_utils import add_document, get_user_documents
from utils.gdrive import upload_file_to_drive

router = Router()

# --- FSM States for Document Upload ---
class DocUploadForm(StatesGroup):
    getting_file = State()
    getting_category = State()

# --- Command Handlers ---
@router.message(Command("upload"))
async def cmd_upload_start(message: types.Message, state: FSMContext):
    """Starts the document upload process."""
    lang = (await state.get_data()).get(UserState.language, "en")
    await message.answer(get_text("docs_upload_prompt", lang))
    await state.set_state(DocUploadForm.getting_file)

@router.message(Command("documents"))
async def cmd_my_documents(message: types.Message, state: FSMContext, session: AsyncSession):
    """Lists the user's uploaded documents."""
    lang = (await state.get_data()).get(UserState.language, "en")
    docs = await get_user_documents(session, message.from_user.id)

    if not docs:
        await message.answer(get_text("docs_no_documents", lang))
        return

    response_parts = [f"*{get_text('docs_list_title', lang)}*"]
    for doc in docs:
        # Note: To resend the file, you'd use the file_id.
        # To link to gdrive, you'd use gdrive_url.
        response_parts.append(get_text("docs_file_entry", lang).format(filename=doc.file_name, category=doc.category))

    await message.answer("\n".join(response_parts), parse_mode="Markdown")

# --- FSM Handlers ---
@router.message(DocUploadForm.getting_file, F.document)
async def process_document(message: types.Message, state: FSMContext):
    """Receives a document and asks for its category."""
    lang = (await state.get_data()).get(UserState.language, "en")

    await state.update_data(
        file_id=message.document.file_id,
        file_unique_id=message.document.file_unique_id,
        file_name=message.document.file_name,
        file_type=message.document.mime_type
    )

    buttons = [
        InlineKeyboardButton(text=get_text("docs_category_general", lang), callback_data="doc_cat_general"),
        InlineKeyboardButton(text=get_text("docs_category_visa", lang), callback_data="doc_cat_visa"),
        InlineKeyboardButton(text=get_text("docs_category_university", lang), callback_data="doc_cat_university"),
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])

    await message.answer(get_text("docs_ask_category", lang), reply_markup=keyboard)
    await state.set_state(DocUploadForm.getting_category)

@router.callback_query(DocUploadForm.getting_category, F.data.startswith("doc_cat_"))
async def process_category_and_save(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Saves the document details to the DB and uploads to Google Drive."""
    category = callback_query.data.split("_")[-1]
    doc_data = await state.get_data()
    lang = doc_data.get(UserState.language, "en")

    await callback_query.message.edit_text("Processing... please wait.")

    # Download file from Telegram to a temporary path
    file = await callback_query.bot.get_file(doc_data["file_id"])
    temp_file_path = f"temp_{doc_data['file_name']}"
    await callback_query.bot.download_file(file.file_path, destination=temp_file_path)

    # Upload to Google Drive
    gdrive_url = upload_file_to_drive(temp_file_path, doc_data['file_name'], doc_data['file_type'])

    # Clean up temporary file
    os.remove(temp_file_path)

    if not gdrive_url:
        await callback_query.message.answer(get_text("docs_upload_failed", lang))
        await state.clear()
        return

    # Save to DB
    await add_document(session, {
        "user_id": callback_query.from_user.id,
        "file_id": doc_data["file_id"],
        "file_unique_id": doc_data["file_unique_id"],
        "file_name": doc_data["file_name"],
        "file_type": doc_data["file_type"],
        "category": category,
        "gdrive_url": gdrive_url
    })

    await callback_query.message.answer(get_text("docs_upload_success", lang).format(filename=doc_data['file_name']))
    await state.clear()
    await callback_query.answer()
