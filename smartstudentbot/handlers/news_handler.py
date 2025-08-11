from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_CHAT_IDS, CHANNEL_ID, FEATURE_FLAGS
from utils.i18n import get_text
from utils.db_utils import add_news, get_latest_news

router = Router()

# --- FSM States for News Posting ---
class NewsForm(StatesGroup):
    getting_title = State()
    getting_content = State()
    getting_media = State()

# --- User-facing command to read news ---
@router.message(Command("news"))
async def cmd_read_news(message: types.Message, session: AsyncSession):
    """Fetches and displays the latest news articles to the user."""
    latest_news = await get_latest_news(session, limit=5)
    if not latest_news:
        await message.answer("No news available at the moment.")
        return

    await message.answer("📰 *Latest News:*", parse_mode="Markdown")
    for article in latest_news:
        text = f"*{article.title}*\n\n{article.content}"
        # This part could be enhanced to show media if available
        await message.answer(text, parse_mode="Markdown")


# --- Admin command to post news ---
@router.message(Command("post_news"), F.from_user.id.in_(ADMIN_CHAT_IDS))
async def cmd_post_news_start(message: types.Message, state: FSMContext):
    """Starts the news posting form for admins."""
    if not FEATURE_FLAGS.get("NEWS", True): return
    await message.answer(get_text("post_news_start", "en"))
    await state.set_state(NewsForm.getting_title)

@router.message(NewsForm.getting_title)
async def process_news_title(message: types.Message, state: FSMContext):
    """Processes the news title."""
    await state.update_data(title=message.text)
    await message.answer(get_text("post_news_ask_content", "en"))
    await state.set_state(NewsForm.getting_content)

@router.message(NewsForm.getting_content, F.text)
async def process_news_text_content(message: types.Message, state: FSMContext):
    """Processes the news content (text only)."""
    await state.update_data(content=message.text)
    await message.answer(get_text("post_news_ask_media", "en"))
    await state.set_state(NewsForm.getting_media)

@router.message(NewsForm.getting_media, Command("skip"))
async def process_skip_media(message: types.Message, state: FSMContext, session: AsyncSession):
    """Handles skipping media and finalizes the post."""
    await state.update_data(media_id=None, media_type=None)
    await message.answer(get_text("post_news_skip", "en"))
    await finalize_news_post(message, state, session)

@router.message(NewsForm.getting_media, F.photo | F.video | F.document)
async def process_news_media_and_finalize(message: types.Message, state: FSMContext, session: AsyncSession):
    """Processes media and finalizes the post. Assumes caption is the content."""
    media_id, media_type = None, None
    if message.photo:
        media_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video:
        media_id, media_type = message.video.file_id, "video"
    elif message.document:
        media_id, media_type = message.document.file_id, "document"

    # If user sends media, the content from previous step is used as caption
    await state.update_data(media_id=media_id, media_type=media_type)
    await finalize_news_post(message, state, session)

async def finalize_news_post(message: types.Message, state: FSMContext, session: AsyncSession):
    """Helper function to save news to DB and publish to channel."""
    data = await state.get_data()

    news_article_data = {
        "title": data.get("title"),
        "content": data.get("content"),
        "media_id": data.get("media_id"),
        "media_type": data.get("media_type"),
        "posted_by": message.from_user.id
    }

    # Save to Database
    await add_news(session, news_article_data)

    # Broadcast to Channel
    if CHANNEL_ID and not DISABLE_EXTERNAL_CALLS:
        try:
            text = f"*{news_article_data['title']}*\n\n{news_article_data['content']}"
            if not news_article_data.get("media_id"):
                 await message.bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
            else:
                # Using a generic sender for all media types
                await message.bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=message.chat.id, message_id=message.message_id, caption=text, parse_mode="Markdown")

            await message.answer(get_text("post_news_success", "en"))
        except Exception as e:
            await message.answer(f"Failed to post to channel: {e}")
    else:
        await message.answer(get_text("post_news_confirm", "en").format(title=news_article_data['title']))

    await state.clear()
