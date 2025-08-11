from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from utils.i18n import get_text
from handlers.cmd_start import UserState
from utils.db_utils import get_all_discounts

router = Router()

@router.message(Command("discounts"))
async def cmd_discounts(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Handler for the /discounts command.
    Displays a list of available student discounts from the database.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    all_discounts = await get_all_discounts(session)

    if not all_discounts:
        await message.answer("Sorry, no discount information is available right now.")
        return

    # Group discounts by category
    discounts_by_category = defaultdict(list)
    for discount in all_discounts:
        discounts_by_category[discount.category].append(discount)

    # Format the message
    message_parts = [f"*{get_text('discounts_title', lang)}*", get_text('discounts_intro', lang)]

    for category, discounts in discounts_by_category.items():
        category_name_key = f"discount_category_{category}"
        message_parts.append(f"\n*{get_text(category_name_key, lang)}*")
        for discount in discounts:
            message_parts.append(
                f"- *{discount.name}*: {discount.description} "
                f"_(Validity: {discount.validity})_"
            )

    response_message = "\n".join(message_parts)

    await message.answer(response_message, parse_mode="Markdown")
