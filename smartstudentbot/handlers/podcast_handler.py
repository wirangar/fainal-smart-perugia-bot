from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from utils.i18n import get_text
from handlers.cmd_start import UserState
from utils.db_utils import get_all_podcasts

router = Router()

@router.message(Command("podcast"))
async def cmd_podcast(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Handler for the /podcast command.
    Displays a list of available podcasts from the database.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    all_podcasts = await get_all_podcasts(session)

    if not all_podcasts:
        await message.answer("Sorry, no podcasts are available right now.")
        return

    await message.answer(f"*{get_text('podcast_title', lang)}*", parse_mode="Markdown")
    await message.answer(get_text('podcast_intro', lang))

    for episode in all_podcasts:
        caption = get_text('podcast_episode_caption', lang).format(
            title=episode.title,
            description=episode.description
        )
        try:
            await message.answer_audio(
                audio=episode.audio_file_id,
                caption=caption,
                title=episode.title,
                duration=episode.duration_seconds
            )
        except Exception as e:
            print(f"Could not send podcast audio for episode {episode.id}: {e}")
            await message.answer(f"Could not load Episode: {episode.title}. The file_id might be invalid.")
