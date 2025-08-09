import json
import os
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.i18n import get_text
from handlers.cmd_start import UserState

router = Router()

def load_info_data():
    """Loads the info data from the JSON file."""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'info.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def format_info_message(data: dict, lang: str) -> tuple[str, types.InlineKeyboardMarkup]:
    """Formats the info data into a message and an inline keyboard."""
    if not data:
        return "Sorry, general information is currently unavailable.", None

    message_parts = [f"*{get_text('info_title', lang)}*\n"]
    keyboard_buttons = []

    for section in data.get("sections", []):
        section_name_key = f"info_section_{section.get('name')}"
        message_parts.append(f"*{get_text(section_name_key, lang)}*")

        if "links" in section:
            for link in section.get("links", []):
                link_name_key = f"info_{link.get('name')}"
                button = InlineKeyboardButton(text=get_text(link_name_key, lang), url=link.get("url"))
                keyboard_buttons.append([button])

        if "numbers" in section:
            for number in section.get("numbers", []):
                number_name_key = f"info_{number.get('name')}"
                message_parts.append(f"- {get_text(number_name_key, lang)}: `{number.get('number')}`")

        message_parts.append("") # Add a newline for spacing

    text = "\n".join(message_parts)
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    return text, keyboard

@router.message(Command("info"))
async def cmd_info(message: types.Message, state: FSMContext):
    """
    Handler for the /info command.
    Displays general information and useful links.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    info_data = load_info_data()

    text, keyboard = format_info_message(info_data, lang)

    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown", disable_web_page_preview=True)
