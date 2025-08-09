import json
import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.i18n import get_text
from handlers.cmd_start import UserState

router = Router()

GUIDE_DATA = {}

def load_guide_data():
    """Loads the guide data from the JSON file into a global variable."""
    global GUIDE_DATA
    file_path = os.path.join(os.path.dirname(__file__), '..', 'guide.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            GUIDE_DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        GUIDE_DATA = {} # Ensure it's empty on failure

# Load data once on module import
load_guide_data()

def create_guide_markup(current_section_key: str, lang: str) -> tuple[str, types.InlineKeyboardMarkup]:
    """
    Generates the text and keyboard for a given section of the guide.
    """
    section = GUIDE_DATA.get("sections", {}).get(current_section_key)
    if not section:
        return "Section not found.", None

    text = get_text(section["text_key"], lang)

    buttons = []
    # Add buttons for child sections
    for child_key in section.get("children", []):
        child_section = GUIDE_DATA.get("sections", {}).get(child_key)
        if child_section:
            # The text for the button is the title of the child section
            button_text_key = child_section.get("text_key").replace("_intro", "").replace("_content", "")
            # A bit of a hacky way to get a topic title key, but it works for this structure
            button_text_key = f"guide_topic_{button_text_key.split('_')[-1]}"
            buttons.append([
                InlineKeyboardButton(text=get_text(button_text_key, lang), callback_data=f"guide_{child_key}")
            ])

    # Add a "Back" button if this is not the root section
    if current_section_key != "root":
        # Find parent
        parent_key = "root" # default
        for key, value in GUIDE_DATA.get("sections", {}).items():
            if current_section_key in value.get("children", []):
                parent_key = key
                break
        buttons.append([
            InlineKeyboardButton(text=get_text("guide_back_button", lang), callback_data=f"guide_{parent_key}")
        ])

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("guide"))
async def cmd_guide(message: types.Message, state: FSMContext):
    """Displays the main menu of the guide."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    text, markup = create_guide_markup("root", lang)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("guide_"))
async def navigate_guide(callback_query: types.CallbackQuery, state: FSMContext):
    """Handles navigation through the guide sections."""
    section_key = callback_query.data.split("_", 1)[1]

    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    text, markup = create_guide_markup(section_key, lang)

    await callback_query.message.edit_text(text, reply_markup=markup)
    await callback_query.answer()
