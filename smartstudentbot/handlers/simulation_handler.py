import json
import os
import random
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from utils.i18n import get_text
from handlers.cmd_start import UserState

router = Router()

SIM_DATA = {}

def load_sim_data():
    """Loads the simulation data from the JSON file."""
    global SIM_DATA
    file_path = os.path.join(os.path.dirname(__file__), '..', 'simulation.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            SIM_DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        SIM_DATA = {}

load_sim_data()

# --- FSM States for Simulation ---
class SimulationGame(StatesGroup):
    in_game = State()

# --- Helper Functions ---
def format_stats(stats: dict, lang: str, day: int, total_days: int) -> str:
    """Formats the player's stats into a readable string."""
    return get_text("sim_status_update", lang).format(
        day=day, total_days=total_days, **stats
    )

async def present_event(message: types.Message, state: FSMContext):
    """Presents a random event to the user."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    event = random.choice(SIM_DATA.get("events", []))
    await state.update_data(current_event=event)

    text = get_text(event["text_key"], lang)
    buttons = []
    for i, choice in enumerate(event["choices"]):
        buttons.append(InlineKeyboardButton(
            text=get_text(choice["text_key"], lang),
            callback_data=f"sim_choice_{i}"
        ))

    markup = InlineKeyboardMarkup(inline_keyboard=[[b] for b in buttons])
    await message.answer(text, reply_markup=markup)

# --- Command and Game Loop Handlers ---
@router.message(Command("simulation"))
async def cmd_simulation_start(message: types.Message, state: FSMContext):
    """Starts a new simulation game."""
    lang = (await state.get_data()).get(UserState.language, "en")

    initial_stats = SIM_DATA.get("initial_stats", {})
    game_state = {
        "stats": initial_stats.copy(),
        "day": 1,
        "total_days": SIM_DATA.get("game_duration_days", 7),
        "lang": lang
    }
    await state.set_data(game_state)
    await state.set_state(SimulationGame.in_game)

    intro_text = get_text("sim_start_intro", lang)
    status_text = format_stats(game_state["stats"], lang, game_state["day"], game_state["total_days"])

    await message.answer(f"{intro_text}\n\n{status_text}")
    await present_event(message, state)

@router.callback_query(SimulationGame.in_game, F.data.startswith("sim_choice_"))
async def process_simulation_choice(callback_query: types.CallbackQuery, state: FSMContext):
    """Processes the user's choice and advances the game."""
    choice_index = int(callback_query.data.split("_")[-1])

    user_data = await state.get_data()
    lang = user_data.get("lang", "en")
    event = user_data.get("current_event")
    choice = event["choices"][choice_index]

    stats = user_data["stats"]
    for key, value in choice["outcomes"].items():
        stats[key] += value
        stats[key] = max(0, stats[key])

    feedback_text = get_text(choice["feedback_key"], lang)
    await callback_query.message.edit_text(f"_{feedback_text}_", parse_mode="Markdown")

    user_data["day"] += 1

    if user_data["day"] > user_data["total_days"]:
        final_status_text = format_stats(stats, lang, user_data["day"] - 1, user_data["total_days"])

        verdict_key = "sim_final_verdict_good"
        if stats["grades"] < 40: verdict_key = "sim_final_verdict_bad_grades"
        elif stats["happiness"] < 40: verdict_key = "sim_final_verdict_unhappy"
        elif stats["money"] <= 0: verdict_key = "sim_final_verdict_broke"

        verdict_text = get_text(verdict_key, lang)

        await callback_query.message.answer(
            f"*{get_text('sim_end_of_week', lang)}*\n\n{final_status_text}\n\n*{verdict_text}*",
            parse_mode="Markdown"
        )
        await state.clear()
    else:
        await state.update_data(stats=stats, day=user_data["day"])
        status_text = format_stats(stats, lang, user_data["day"], user_data["total_days"])
        await callback_query.message.answer(status_text)
        await present_event(callback_query.message, state)

    await callback_query.answer()
