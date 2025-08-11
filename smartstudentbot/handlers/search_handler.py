import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from utils.i18n import get_text
from handlers.cmd_start import UserState
from models_db import News, Discount
from handlers.guide_handler import GUIDE_DATA # To search in guide

router = Router()

async def search_in_db(session: AsyncSession, query: str):
    """Performs a LIKE search across multiple database tables."""
    results = []
    # Search News
    news_stmt = select(News).where(or_(News.title.ilike(f"%{query}%"), News.content.ilike(f"%{query}%")))
    news_results = (await session.execute(news_stmt)).scalars().all()
    for item in news_results:
        results.append({"type": "news", "item": item})

    # Search Discounts
    disc_stmt = select(Discount).where(or_(Discount.name.ilike(f"%{query}%"), Discount.description.ilike(f"%{query}%")))
    disc_results = (await session.execute(disc_stmt)).scalars().all()
    for item in disc_results:
        results.append({"type": "discount", "item": item})

    return results

def search_in_guide(query: str, lang: str):
    """Performs a simple text search in the guide data."""
    results = []
    query = query.lower()
    for key, section in GUIDE_DATA.get("sections", {}).items():
        text_key = section["text_key"]
        text_content = get_text(text_key, lang).lower()
        if query in text_content:
            title_key = text_key.replace("_intro", "").replace("_content", "")
            title_key = f"guide_topic_{title_key.split('_')[-1]}"
            results.append({"type": "guide", "item": {"title": get_text(title_key, lang)}})
    return results

@router.message(Command("search"))
async def cmd_search(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Handler for the /search command.
    Searches across various bot content.
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(get_text("search_prompt", lang))
        return

    query = args[1]

    # Perform searches in parallel
    db_results, guide_results = await asyncio.gather(
        search_in_db(session, query),
        asyncio.to_thread(search_in_guide, query, lang) # Run sync function in thread
    )

    all_results = db_results + guide_results

    if not all_results:
        await message.answer(get_text("search_no_results", lang).format(query=query))
        return

    response_parts = [get_text("search_results_title", lang).format(query=query)]
    for res in all_results:
        if res["type"] == "news":
            response_parts.append(get_text("search_result_in_news", lang).format(title=res["item"].title))
        elif res["type"] == "discount":
            response_parts.append(get_text("search_result_in_discounts", lang).format(name=res["item"].name, description=res["item"].description))
        elif res["type"] == "guide":
            response_parts.append(get_text("search_result_in_guide", lang).format(section_title=res["item"]["title"]))

    await message.answer("\n- ".join(response_parts), parse_mode="Markdown")
