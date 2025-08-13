import asyncio
import re
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from utils.i18n import get_text
from handlers.cmd_start import UserState
from models_db import News, Discount
from handlers.guide_handler import GUIDE_DATA

router = Router()

def calculate_score(text: str, query: str) -> int:
    """A simple scoring function based on query occurrences."""
    return text.lower().count(query.lower())

async def search_in_db(session: AsyncSession, query: str, category: str | None = None):
    """Performs a LIKE search across multiple database tables with scoring."""
    results = []
    search_query = f"%{query}%"

    if not category or category == "news":
        news_stmt = select(News).where(or_(News.title.ilike(search_query), News.content.ilike(search_query)))
        news_results = (await session.execute(news_stmt)).scalars().all()
        for item in news_results:
            score = calculate_score(item.title, query) + calculate_score(item.content, query)
            results.append({"type": "news", "item": item, "score": score})

    if not category or category == "discounts":
        disc_stmt = select(Discount).where(or_(Discount.name.ilike(search_query), Discount.description.ilike(search_query)))
        disc_results = (await session.execute(disc_stmt)).scalars().all()
        for item in disc_results:
            score = calculate_score(item.name, query) + calculate_score(item.description, query)
            results.append({"type": "discount", "item": item, "score": score})

    return results

def search_in_guide(query: str, lang: str):
    """Performs a simple text search in the guide data with scoring."""
    results = []
    for key, section in GUIDE_DATA.get("sections", {}).items():
        text_content = get_text(section["text_key"], lang)
        score = calculate_score(text_content, query)
        if score > 0:
            title_key = section["text_key"].replace("_intro", "").replace("_content", "")
            title_key = f"guide_topic_{title_key.split('_')[-1]}"
            results.append({"type": "guide", "item": {"title": get_text(title_key, lang)}, "score": score})
    return results

@router.message(Command("search"))
async def cmd_search(message: types.Message, state: FSMContext, session: AsyncSession):
    """
    Handler for the /search command.
    Searches across various bot content, with optional category filtering.
    Syntax: /search [category:news|discounts|guide] <query>
    """
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(get_text("search_prompt", lang))
        return

    full_query = args[1]
    category = None
    query = full_query

    # Check for category filter e.g., "news: my query"
    match = re.match(r"(\w+):\s*(.*)", full_query)
    if match:
        cat, q = match.groups()
        if cat in ["news", "discounts", "guide"]:
            category = cat
            query = q

    db_results, guide_results = await asyncio.gather(
        search_in_db(session, query, category),
        asyncio.to_thread(search_in_guide, query, lang)
    )

    # Filter guide results if a non-guide category was specified
    if category and category != "guide":
        guide_results = []

    all_results = db_results + guide_results

    if not all_results:
        await message.answer(get_text("search_no_results", lang).format(query=query))
        return

    # Sort results by score, descending
    all_results.sort(key=lambda x: x["score"], reverse=True)

    response_parts = [get_text("search_results_title", lang).format(query=query)]
    for res in all_results[:10]: # Limit to top 10 results
        if res["type"] == "news":
            response_parts.append(get_text("search_result_in_news", lang).format(title=res["item"].title))
        elif res["type"] == "discount":
            response_parts.append(get_text("search_result_in_discounts", lang).format(name=res["item"].name, description=res["item"].description))
        elif res["type"] == "guide":
            response_parts.append(get_text("search_result_in_guide", lang).format(section_title=res["item"]["title"]))

    await message.answer("\n- ".join(response_parts), parse_mode="Markdown")
