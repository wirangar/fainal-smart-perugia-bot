import json
import os
from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_CHAT_IDS, CHANNEL_ID, FEATURE_FLAGS
from utils.i18n import get_text
# from utils.db_utils import save_news # Placeholder for DB logic
# from utils.gdrive import upload_file # Placeholder for file upload logic

router = Router()

# --- FSM States for News Posting ---
class NewsForm(StatesGroup):
    getting_title = State()
    getting_content = State()
    getting_media = State()
    getting_caption = State()

def save_news_to_json(news_data: dict):
    """Appends a new news article to the news.json file."""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'news.json')
    try:
        with open(file_path, 'r+', encoding='utf-8') as f:
            news_list = json.load(f)
            news_list.append(news_data)
            f.seek(0)
            json.dump(news_list, f, indent=2, ensure_ascii=False)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is empty, create a new list
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([news_data], f, indent=2, ensure_ascii=False)


@router.message(Command("post_news"), F.from_user.id.in_(ADMIN_CHAT_IDS))
async def cmd_post_news_start(message: types.Message, state: FSMContext):
    """Starts the news posting form for admins."""
    if not FEATURE_FLAGS.get("NEWS", True):
        return

    # For simplicity, we assume admin lang is English for prompts
    lang = "en"
    await message.answer(get_text("post_news_start", lang))
    await state.set_state(NewsForm.getting_title)

@router.message(NewsForm.getting_title)
async def process_news_title(message: types.Message, state: FSMContext):
    """Processes the news title."""
    await state.update_data(title=message.text)
    await message.answer(get_text("post_news_ask_content", "en"))
    await state.set_state(NewsForm.getting_content)

@router.message(NewsForm.getting_content)
async def process_news_content(message: types.Message, state: FSMContext):
    """Processes the news content."""
    await state.update_data(content=message.text)
    await message.answer(get_text("post_news_ask_media", "en"))
    await state.set_state(NewsForm.getting_media)

@router.message(NewsForm.getting_media, Command("skip"))
async def process_skip_media(message: types.Message, state: FSMContext):
    """Handles skipping the media attachment."""
    await state.update_data(media_id=None, media_type=None)
    await message.answer(get_text("post_news_skip", "en"))
    # Since we have all we need, let's finalize
    await finalize_news_post(message, state)

@router.message(NewsForm.getting_media, F.photo | F.video | F.document)
async def process_news_media(message: types.Message, state: FSMContext):
    """Processes the optional media for the news."""
    media_id = None
    media_type = None
    if message.photo:
        media_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video:
        media_id = message.video.file_id
        media_type = "video"
    elif message.document:
        media_id = message.document.file_id
        media_type = "document"

    await state.update_data(media_id=media_id, media_type=media_type)
    await message.answer(get_text("post_news_ask_caption", "en"))
    await state.set_state(NewsForm.getting_caption)

@router.message(NewsForm.getting_caption)
async def process_news_caption(message: types.Message, state: FSMContext):
    """Processes the caption and finalizes the post."""
    await state.update_data(caption=message.text)
    await finalize_news_post(message, state)


async def finalize_news_post(message: types.Message, state: FSMContext):
    """Helper function to save and publish the news article."""
    data = await state.get_data()

    news_article = {
        "id": int(datetime.now().timestamp()),
        "title": data.get("title"),
        "content": data.get("content"),
        "media_id": data.get("media_id"),
        "media_type": data.get("media_type"),
        "caption": data.get("caption", data.get("content", ""))[:1024], # Caption limit
        "timestamp": datetime.now().isoformat(),
        "posted_by": message.from_user.id
    }

    # Save to JSON file
    save_news_to_json(news_article)

    # Broadcast to Channel
    if CHANNEL_ID:
        try:
            text = f"*{news_article['title']}*\n\n{news_article['content']}"
            if not news_article.get("media_id"):
                 await message.bot.send_message(CHANNEL_ID, text, parse_mode="Markdown")
            elif news_article["media_type"] == "photo":
                await message.bot.send_photo(CHANNEL_ID, news_article["media_id"], caption=text, parse_mode="Markdown")
            elif news_article["media_type"] == "video":
                await message.bot.send_video(CHANNEL_ID, news_article["media_id"], caption=text, parse_mode="Markdown")
            elif news_article["media_type"] == "document":
                await message.bot.send_document(CHANNEL_ID, news_article["media_id"], caption=text, parse_mode="Markdown")

            await message.answer(get_text("post_news_success", "en"))
        except Exception as e:
            await message.answer(f"Failed to post to channel: {e}")
    else:
        await message.answer(get_text("post_news_confirm", "en").format(title=news_article['title']))

    await state.clear()
