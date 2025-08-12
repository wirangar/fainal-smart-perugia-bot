from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from utils.i18n import get_text
from handlers.cmd_start import UserState
from utils.db_utils import delete_user_data

router = Router()

@router.message(Command("delete_me"))
async def cmd_delete_me(message: types.Message, state: FSMContext):
    """Asks for confirmation before deleting all user data."""
    lang = (await state.get_data()).get(UserState.language, "en")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text("privacy_delete_confirm_button", lang), callback_data="delete_me_confirm"),
            InlineKeyboardButton(text=get_text("privacy_delete_cancel_button", lang), callback_data="delete_me_cancel"),
        ]
    ])

    await message.answer(get_text("privacy_delete_warning", lang), reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "delete_me_confirm")
async def process_delete_me_confirm(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Deletes all user data upon confirmation."""
    lang = (await state.get_data()).get(UserState.language, "en")

    await callback_query.message.edit_text("Deleting your data...")

    success = await delete_user_data(session, callback_query.from_user.id)

    if success:
        await callback_query.message.edit_text(get_text("privacy_delete_success", lang))
    else:
        # This case should ideally not happen if the user exists
        await callback_query.message.edit_text("Could not find your data to delete.")

    await state.clear() # Clear FSM state as well
    await callback_query.answer()

@router.callback_query(F.data == "delete_me_cancel")
async def process_delete_me_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    """Cancels the data deletion process."""
    lang = (await state.get_data()).get(UserState.language, "en")
    await callback_query.message.edit_text(get_text("privacy_delete_cancelled", lang))
    await callback_query.answer()
