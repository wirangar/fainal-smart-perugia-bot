import json
import os
import base64
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.i18n import get_text
from handlers.cmd_start import UserState

router = Router()
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), '..', 'resources')
ITEMS_PER_PAGE = 5

def get_resource_files():
    """Gets a list of all .json files in the resources directory."""
    if not os.path.exists(RESOURCES_DIR):
        return []
    return [f for f in os.listdir(RESOURCES_DIR) if f.endswith(".json")]

async def build_resources_page(lang: str, page: int = 0):
    """Builds the text and keyboard for a specific page of resources."""
    files = get_resource_files()
    if not files:
        return get_text("resources_none_found", lang), None

    total_pages = (len(files) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    start_index = page * ITEMS_PER_PAGE
    end_index = start_index + ITEMS_PER_PAGE
    page_files = files[start_index:end_index]

    text = get_text("resources_intro", lang)

    keyboard = []
    for filename in page_files:
        # We encode the filename to avoid issues with special characters in callback data
        encoded_filename = base64.urlsafe_b64encode(filename.encode()).decode()
        keyboard.append([InlineKeyboardButton(text=filename.replace('.json', ''), callback_data=f"resource_view_{encoded_filename}")])

    # Pagination buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=get_text("resources_prev_button", lang), callback_data=f"resource_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=get_text("resources_page_display", lang).format(current_page=page+1, total_pages=total_pages), callback_data="noop"))
    if end_index < len(files):
        nav_buttons.append(InlineKeyboardButton(text=get_text("resources_next_button", lang), callback_data=f"resource_page_{page+1}"))
    keyboard.append(nav_buttons)

    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("resources"))
async def cmd_resources(message: types.Message, state: FSMContext):
    """Displays the first page of resources."""
    lang = (await state.get_data()).get(UserState.language, "en")
    text, markup = await build_resources_page(lang, page=0)
    await message.answer(text, reply_markup=markup)

@router.callback_query(F.data.startswith("resource_page_"))
async def handle_resource_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles next/previous page buttons for resources."""
    page = int(callback_query.data.split("_")[-1])
    lang = (await state.get_data()).get(UserState.language, "en")
    text, markup = await build_resources_page(lang, page=page)
    await callback_query.message.edit_text(text, reply_markup=markup)
    await callback_query.answer()

@router.callback_query(F.data.startswith("resource_view_"))
async def view_resource_content(callback_query: types.CallbackQuery, state: FSMContext):
    """Displays the content of a selected JSON resource file."""
    encoded_filename = callback_query.data.split("_")[-1]
    filename = base64.urlsafe_b64decode(encoded_filename.encode()).decode()
    lang = (await state.get_data()).get(UserState.language, "en")

    file_path = os.path.join(RESOURCES_DIR, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Format the content for display
        display_name = data.get("display_name", filename)
        description = data.get("description", "No description available.")

        response_parts = [
            f"*{get_text('resource_content_title', lang).format(display_name=display_name)}*",
            f"_{get_text('resource_description', lang).format(description=description)}_",
            "---"
        ]

        for item in data.get("content", []):
            response_parts.append(f"*{item.get('title')}*")
            response_parts.append(item.get("text", ""))

        response_text = "\n".join(response_parts)
        await callback_query.message.answer(response_text, parse_mode="Markdown")

    except Exception as e:
        await callback_query.message.answer(f"Error reading resource: {e}")

    await callback_query.answer()
