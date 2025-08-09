import json
import os
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from utils.i18n import get_text
from handlers.cmd_start import UserState # To get user language state

router = Router()

def load_cost_data():
    """Loads the cost of living data from the JSON file."""
    # It's better to load this once and cache it, but for simplicity, we'll read it each time.
    file_path = os.path.join(os.path.dirname(__file__), '..', 'cost_of_living.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def format_cost_message(data: dict, lang: str) -> str:
    """Formats the cost of living data into a user-friendly Markdown message."""
    if not data:
        return "Sorry, cost of living data is currently unavailable."

    currency_symbol = "€" if data.get('currency') == 'EUR' else "$"

    message_parts = [f"*{get_text('cost_of_living_title', lang)}*"]

    for category in data.get("categories", []):
        category_name_key = f"cost_category_{category.get('name')}"
        message_parts.append(f"\n*{get_text(category_name_key, lang)}*")

        for item in category.get("items", []):
            price_range = item.get("price_range")
            unit_key = f"cost_unit_{item.get('unit').replace(' ', '_')}"
            unit_text = get_text(unit_key, lang)

            price_str = f"{price_range[0]}"
            if len(price_range) > 1 and price_range[0] != price_range[1]:
                price_str += f" - {price_range[1]}"

            message_parts.append(
                f"- {item.get('description')}: *{price_str} {currency_symbol}* ({unit_text})"
            )

    message_parts.append(f"\n_{get_text('data_source', lang).format(source=data.get('source'))}_")

    return "\n".join(message_parts)


@router.message(Command("cost"))
async def cmd_cost(message: types.Message, state: FSMContext):
    """
    Handler for the /cost command.
    Displays the estimated cost of living in Perugia.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en") # Default to English

    cost_data = load_cost_data()

    response_message = format_cost_message(cost_data, lang)

    await message.answer(response_message, parse_mode="Markdown")
