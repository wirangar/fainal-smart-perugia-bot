import json
import os
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from utils.i18n import get_text
from handlers.cmd_start import UserState

router = Router()

def load_podcast_data():
    """Loads the podcast data from the JSON file."""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'podcasts.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

@router.message(Command("podcast"))
async def cmd_podcast(message: types.Message, state: FSMContext):
    """
    Handler for the /podcast command.
    Displays a list of available podcasts.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    podcast_data = load_podcast_data()

    if not podcast_data or not podcast_data.get("podcasts"):
        await message.answer("Sorry, no podcasts are available right now.")
        return

    await message.answer(f"*{get_text('podcast_title', lang)}*", parse_mode="Markdown")
    await message.answer(get_text('podcast_intro', lang))

    for episode in podcast_data["podcasts"]:
        caption = get_text('podcast_episode_caption', lang).format(
            title=episode['title'],
            description=episode['description']
        )
        # We send each podcast as a separate audio message
        try:
            await message.answer_audio(
                audio=episode['audio_file_id'],
                caption=caption,
                title=episode['title'],
                duration=episode['duration_seconds']
            )
        except Exception as e:
            # This will fail if the file_id is invalid.
            # In a real bot, these IDs would be valid.
            print(f"Could not send podcast audio for episode {episode['id']}: {e}")
            await message.answer(f"Could not load Episode: {episode['title']}. The file_id might be invalid.")
