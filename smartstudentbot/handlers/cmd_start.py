from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.i18n import get_text

router = Router()

# Define a simple state to store user data
class UserState:
    language = "user_language"

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Handler for the /start command.
    Greets the user and shows language selection buttons.
    """
    # Create the language selection keyboard
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_text("lang_button_en", "en"), callback_data="set_lang_en"),
                InlineKeyboardButton(text=get_text("lang_button_fa", "fa"), callback_data="set_lang_fa"),
                InlineKeyboardButton(text=get_text("lang_button_it", "it"), callback_data="set_lang_it"),
            ]
        ]
    )

    # Send the welcome message with the keyboard
    # We use the English text here as no language is set yet.
    await message.answer(get_text("welcome_message", "en"), reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith("set_lang_"))
async def process_language_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Handler for language selection callback.
    Sets the user's language and displays the main menu (placeholder).
    """
    lang_code = callback_query.data.split("_")[-1]

    # Store the selected language in the user's state
    await state.update_data({UserState.language: lang_code})

    # Acknowledge the callback query
    await callback_query.answer()

    # Send a confirmation message in the selected language
    await callback_query.message.edit_text(get_text("language_selected", lang_code))

    # TODO: Show the main menu after language selection
    # For now, we'll just leave the confirmation message.
    # await show_main_menu(callback_query.message, state)
