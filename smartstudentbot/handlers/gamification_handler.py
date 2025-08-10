from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from utils.i18n import get_text
from handlers.cmd_start import UserState
from models_db import UserPoints, UserAchievement
from utils.gamification_utils import get_user_points

router = Router()

@router.message(Command("points"))
async def cmd_points(message: types.Message, state: FSMContext, session: AsyncSession):
    """Displays the user's current points and achievements."""
    user_data = await state.get_data()
    lang = user_data.get(UserState.language, "en")
    user_id = message.from_user.id

    # Get user's points
    user_points = await get_user_points(session, user_id)

    # Get user's achievements
    stmt = select(UserAchievement).where(UserAchievement.user_id == user_id)
    result = await session.execute(stmt)
    achievements = result.scalars().all()

    # Build the response message
    message_parts = [
        f"*{get_text('gamification_points_title', lang)}*",
        "---",
        get_text('gamification_total_points', lang).format(points=user_points.points)
    ]

    if not achievements:
        message_parts.append(f"\n_{get_text('gamification_no_achievements', lang)}_")
    else:
        message_parts.append(f"\n*{get_text('gamification_achievements_title', lang)}*")
        for ach in achievements:
            ach_name_key = f"achievement_{ach.achievement_id.name}"
            ach_name = get_text(ach_name_key, lang)
            # You could add descriptions from ACHIEVEMENT_DEFINITIONS here too
            message_parts.append(f"- 🏆 {ach_name}")

    response_message = "\n".join(message_parts)

    await message.answer(response_message, parse_mode="Markdown")
