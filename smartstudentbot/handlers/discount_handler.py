import json
import os
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from collections import defaultdict

from utils.i18n import get_text
from handlers.cmd_start import UserState

router = Router()

def load_discount_data():
    """Loads the discount data from the JSON file."""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'discounts.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

@router.message(Command("discounts"))
async def cmd_discounts(message: types.Message, state: FSMContext):
    """
    Handler for the /discounts command.
    Displays a list of available student discounts, grouped by category.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    discount_data = load_discount_data()

    if not discount_data or not discount_data.get("discounts"):
        await message.answer("Sorry, no discount information is available right now.")
        return

    # Group discounts by category
    discounts_by_category = defaultdict(list)
    for discount in discount_data["discounts"]:
        discounts_by_category[discount["category"]].append(discount)

    # Format the message
    message_parts = [f"*{get_text('discounts_title', lang)}*", get_text('discounts_intro', lang)]

    for category, discounts in discounts_by_category.items():
        category_name_key = f"discount_category_{category}"
        message_parts.append(f"\n*{get_text(category_name_key, lang)}*")
        for discount in discounts:
            message_parts.append(
                f"- *{discount['name']}*: {discount['description']} "
                f"_(Validity: {discount['validity']})_"
            )

    response_message = "\n".join(message_parts)

    await message.answer(response_message, parse_mode="Markdown")
