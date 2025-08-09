import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import cmd_start
from utils.i18n import get_text

@pytest.mark.unit
@pytest.mark.asyncio
async def test_cmd_start():
    # 1. Setup
    bot = MagicMock()
    bot.answer = AsyncMock() # Mock the bot's answer method

    # Use MemoryStorage for testing FSM
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(cmd_start.router)

    # Mock message and state
    message = MagicMock()
    message.answer = bot.answer # Redirect message.answer to our mock
    state = dp.fsm.get_context(bot=bot, user_id=123, chat_id=456)

    # 2. Execution
    await cmd_start.cmd_start(message, state=state)

    # 3. Assertions
    # Check that the answer method was called once
    message.answer.assert_called_once()

    # Check the content of the call
    args, kwargs = message.answer.call_args
    assert args[0] == get_text("welcome_message", "en")
    assert "reply_markup" in kwargs

    # Check keyboard buttons
    keyboard = kwargs["reply_markup"]
    buttons = keyboard.inline_keyboard[0]
    assert len(buttons) == 3
    assert buttons[0].text == get_text("lang_button_en", "en")
    assert buttons[0].callback_data == "set_lang_en"
    assert buttons[1].text == get_text("lang_button_fa", "fa")
    assert buttons[2].text == get_text("lang_button_it", "it")


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("lang_code, expected_text_key", [
    ("en", "language_selected"),
    ("fa", "language_selected"),
    ("it", "language_selected"),
])
async def test_process_language_selection(lang_code, expected_text_key):
    # 1. Setup
    bot = MagicMock()
    bot.edit_message_text = AsyncMock()

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(cmd_start.router)

    # Mock CallbackQuery and its message
    callback_query = MagicMock()
    callback_query.data = f"set_lang_{lang_code}"
    callback_query.message.edit_text = bot.edit_message_text
    callback_query.answer = AsyncMock()

    state = dp.fsm.get_context(bot=bot, user_id=123, chat_id=456)

    # 2. Execution
    await cmd_start.process_language_selection(callback_query, state=state)

    # 3. Assertions
    # Check that the callback was answered
    callback_query.answer.assert_called_once()

    # Check that the message text was edited
    callback_query.message.edit_text.assert_called_once()
    args, kwargs = callback_query.message.edit_text.call_args
    assert args[0] == get_text(expected_text_key, lang_code)

    # Check that the FSM state was updated correctly
    user_data = await state.get_data()
    assert user_data[cmd_start.UserState.language] == lang_code
