from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models_db import User, UserPoints, UserAchievement, PointsAction, Achievement

# Define how many points each action is worth
ACTION_POINTS = {
    PointsAction.COMPLETE_PROFILE: 25,
    PointsAction.SHARE_SUCCESS_STORY: 50,
    PointsAction.DAILY_LOGIN: 5,
}

# Define achievements and their requirements
ACHIEVEMENT_DEFINITIONS = {
    Achievement.FIRST_STEPS: {"description": "Complete your first profile (e.g., roommate)."},
    Achievement.STORY_TELLER: {"description": "Share a success story."},
    Achievement.COMMUNITY_HERO: {"description": "Reach 100 total points."},
}

async def get_user_points(session: AsyncSession, user_id: int) -> UserPoints:
    """Gets or creates a user's points profile."""
    stmt = select(UserPoints).where(UserPoints.user_id == user_id)
    result = await session.execute(stmt)
    user_points = result.scalar_one_or_none()

    if not user_points:
        user_points = UserPoints(user_id=user_id, points=0)
        session.add(user_points)
        await session.commit()
        await session.refresh(user_points)

    return user_points

async def award_points(session: AsyncSession, user_id: int, action: PointsAction):
    """Awards points to a user for a specific action and checks for new achievements."""
    points_to_add = ACTION_POINTS.get(action, 0)
    if points_to_add == 0:
        return

    user_points = await get_user_points(session, user_id)
    user_points.points += points_to_add

    await session.commit()
    print(f"Awarded {points_to_add} points to user {user_id} for action {action.name}. New total: {user_points.points}")

    # After awarding points, check for any new achievements
    await check_and_grant_achievements(session, user_id, user_points)

async def has_achievement(session: AsyncSession, user_id: int, achievement: Achievement) -> bool:
    """Checks if a user already has a specific achievement."""
    stmt = select(UserAchievement).where(UserAchievement.user_id == user_id, UserAchievement.achievement_id == achievement)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None

async def grant_achievement(session: AsyncSession, user_id: int, achievement: Achievement):
    """Grants a new achievement to a user if they don't already have it."""
    if not await has_achievement(session, user_id, achievement):
        new_achievement = UserAchievement(user_id=user_id, achievement_id=achievement)
        session.add(new_achievement)
        await session.commit()
        print(f"User {user_id} unlocked achievement: {achievement.name}")
        # In a real scenario, you'd send a notification message to the user here.

async def check_and_grant_achievements(session: AsyncSession, user_id: int, user_points: UserPoints):
    """Checks all achievement conditions for a user and grants them if met."""
    # This is a simplified checker. A more complex system might check other conditions.

    # Check for points-based achievements
    if user_points.points >= 100:
        await grant_achievement(session, user_id, Achievement.COMMUNITY_HERO)

    # Other event-based achievements would be granted directly by the award_points function
    # by mapping an action to an achievement.
    if await has_action(session, user_id, PointsAction.SHARE_SUCCESS_STORY): # Placeholder for a real check
         await grant_achievement(session, user_id, Achievement.STORY_TELLER)

async def has_action(session: AsyncSession, user_id: int, action: PointsAction):
    # This is a placeholder. A real implementation would need to query an audit log
    # or check for the existence of a success story, profile, etc.
    return True # Assume true for now for demonstration
