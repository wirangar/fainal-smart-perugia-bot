from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.i18n import get_text
from handlers.cmd_start import UserState
from config import ISEE_THRESHOLD

router = Router()

# --- FSM States ---
class IseeForm(StatesGroup):
    getting_income = State()
    getting_property = State()
    getting_family_members = State()

# --- ISEE Calculation Logic ---
FAMILY_COEFFICIENTS = {
    1: 1.00, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85,
    # Add more if needed, this is a simplified table
    6: 3.20, 7: 3.55, 8: 3.90, 9: 4.25, 10: 4.60
}

def calculate_isee(income: float, property_size: float, family_members: int) -> tuple[float, str]:
    """Calculates ISEE value and scholarship status."""
    coefficient = FAMILY_COEFFICIENTS.get(family_members)
    if not coefficient:
        raise ValueError("Invalid number of family members")

    # Formula from the prompt
    property_value = property_size * 500
    isp = income + (property_value * 0.2)
    isee_value = isp / coefficient

    # Determine scholarship status
    percentage = (isee_value / ISEE_THRESHOLD) * 100
    if percentage <= 55:
        status_key = "isee_status_full"
    elif percentage <= 71.5:
        status_key = "isee_status_mid"
    elif percentage <= 100:
        status_key = "isee_status_partial"
    else:
        status_key = "isee_status_none"

    return isee_value, status_key


# --- FSM Handlers ---
@router.message(Command("isee"))
async def cmd_isee_start(message: types.Message, state: FSMContext):
    """Starts the ISEE calculation form."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    await message.answer(get_text("isee_intro", lang))
    await message.answer(get_text("isee_ask_income", lang))
    await state.set_state(IseeForm.getting_income)

@router.message(IseeForm.getting_income)
async def process_income(message: types.Message, state: FSMContext):
    """Processes the income and asks for property size."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    try:
        income = float(message.text)
        await state.update_data(income=income)
        await message.answer(get_text("isee_ask_property", lang))
        await state.set_state(IseeForm.getting_property)
    except (ValueError, TypeError):
        await message.answer(get_text("isee_invalid_input", lang))

@router.message(IseeForm.getting_property)
async def process_property(message: types.Message, state: FSMContext):
    """Processes property size and asks for family members."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    try:
        property_size = float(message.text)
        await state.update_data(property_size=property_size)
        await message.answer(get_text("isee_ask_family_members", lang))
        await state.set_state(IseeForm.getting_family_members)
    except (ValueError, TypeError):
        await message.answer(get_text("isee_invalid_input", lang))

@router.message(IseeForm.getting_family_members)
async def process_family_members(message: types.Message, state: FSMContext):
    """Processes family members, calculates, and shows the result."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    try:
        family_members = int(message.text)
        if family_members not in FAMILY_COEFFICIENTS:
            await message.answer(get_text("isee_family_coefficient_error", lang))
            return

        # All data collected, now calculate
        income = user_data.get("income")
        property_size = user_data.get("property_size")

        isee_value, status_key = calculate_isee(income, property_size, family_members)

        status_text = get_text(status_key, lang)

        result_message = "\n".join([
            f"*{get_text('isee_result_title', lang)}*",
            "---",
            get_text('isee_value', lang).format(isee_value=isee_value),
            get_text('isee_scholarship_status', lang).format(status=status_text)
        ])

        await message.answer(result_message, parse_mode="Markdown")
        await state.clear() # Clear the state after finishing

    except (ValueError, TypeError):
        await message.answer(get_text("isee_invalid_input", lang))
    except Exception as e:
        await message.answer(f"An unexpected error occurred: {e}")
        await state.clear()
