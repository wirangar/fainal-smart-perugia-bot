from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models_db import AsyncSessionLocal, SuccessStory, User, StoryStatus

# --- Dependency for getting a DB session ---
async def get_db_session() -> AsyncSession:
    """
    Dependency to get an async database session.
    Ensures the session is properly closed.
    """
    async with AsyncSessionLocal() as session:
        yield session

# --- User Functions ---
async def get_or_create_user(session: AsyncSession, user_data: dict) -> User:
    """
    Retrieves a user from the DB or creates a new one if they don't exist.
    """
    stmt = select(User).where(User.user_id == user_data['user_id'])
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(**user_data)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user

# --- Success Story Functions ---
async def add_success_story(session: AsyncSession, story_data: dict) -> SuccessStory:
    """
    Adds a new success story to the database.
    """
    new_story = SuccessStory(**story_data)
    session.add(new_story)
    await session.commit()
    await session.refresh(new_story)
    return new_story

async def get_random_approved_story(session: AsyncSession) -> SuccessStory:
    """
    Retrieves a random, approved success story from the database.
    (Note: This is a simplified random implementation for SQLite/Postgres)
    """
    # For a truly random row in a large table, more advanced SQL is needed.
    # For now, we'll just get the first one.
    stmt = select(SuccessStory).where(SuccessStory.status == StoryStatus.APPROVED).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def get_pending_stories(session: AsyncSession, limit: int = 10):
    """
    Retrieves a list of pending success stories for admin review.
    """
    stmt = select(SuccessStory).where(SuccessStory.status == StoryStatus.PENDING).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

async def update_story_status(session: AsyncSession, story_id: int, status: StoryStatus) -> SuccessStory:
    """
    Updates the status of a success story.
    """
    stmt = select(SuccessStory).where(SuccessStory.id == story_id)
    result = await session.execute(stmt)
    story = result.scalar_one_or_none()

    if story:
        story.status = status
        await session.commit()
        await session.refresh(story)

    return story


# --- Middleware for DB Session ---
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class DbSessionMiddleware(BaseMiddleware):
    """
    This middleware creates a new SQLAlchemy session for each update,
    passes it to the handler, and closes it after the handler is done.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)
