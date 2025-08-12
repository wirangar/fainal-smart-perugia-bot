from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    BigInteger,
    Text,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
import enum

from config import DATABASE_URL, SQLITE_DB

# --- Base and Engine Setup ---
Base = declarative_base()

# Use async engine for the application
# The DATABASE_URL from config will determine if it's PostgreSQL or SQLite
DB_CONNECT_URL = DATABASE_URL or f"sqlite+aiosqlite:///{SQLITE_DB}"
async_engine = create_async_engine(DB_CONNECT_URL)

# Create a configured "AsyncSession" class
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --- Enums ---
class StoryStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class EventType(enum.Enum):
    APPOINTMENT = "appointment"
    SEMINAR = "seminar"
    WORKSHOP = "workshop"

class AccessLevel(enum.Enum):
    PRIVATE = "private" # Only the user can see
    ADMIN_ONLY = "admin_only" # User and admins
    PUBLIC = "public" # Everyone

class EventStatus(enum.Enum):
    PENDING = "pending" # For appointments needing confirmation
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FULL = "full"

class PointsAction(enum.Enum):
    COMPLETE_PROFILE = "complete_profile"
    SHARE_SUCCESS_STORY = "share_success_story"
    DAILY_LOGIN = "daily_login"
    RECEIVE_FEEDBACK_RATING = "receive_feedback_rating"

class Achievement(enum.Enum):
    FIRST_STEPS = "first_steps" # Completed profile
    STORY_TELLER = "story_teller" # Shared a success story
    COMMUNITY_HERO = "community_hero" # Reached 100 points
    VETERAN = "veteran" # Used the bot for 30 days

# --- Table Models ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String)
    first_name = Column(String)
    language_code = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}')>"

class SuccessStory(Base):
    __tablename__ = "success_stories"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    story_text = Column(Text, nullable=False)
    media_id = Column(String)
    media_type = Column(String) # 'photo', 'video', etc.
    status = Column(SAEnum(StoryStatus), default=StoryStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SuccessStory(id={self.id}, user_id={self.user_id}, status='{self.status.name}')>"

class RoommateProfile(Base):
    __tablename__ = "roommate_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    budget_min = Column(Integer)
    budget_max = Column(Integer)
    location_preferences = Column(Text) # Comma-separated list of neighborhoods
    habits = Column(Text) # e.g., "non-smoker, quiet, tidy"
    about_me = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RoommateProfile(user_id={self.user_id}, is_active={self.is_active})>"

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False) # e.g., 1-5
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Feedback(user_id={self.user_id}, rating={self.rating})>"

class UserPoints(Base):
    __tablename__ = "user_points"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    points = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserPoints(user_id={self.user_id}, points={self.points})>"

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(SAEnum(Achievement), nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserAchievement(user_id={self.user_id}, achievement='{self.achievement_id.name}')>"

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    event_type = Column(SAEnum(EventType), nullable=False)
    event_datetime = Column(DateTime, nullable=False)
    location = Column(String)
    max_attendees = Column(Integer, default=0) # 0 for unlimited
    status = Column(SAEnum(EventStatus), default=EventStatus.CONFIRMED, nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True) # Can be user or admin

    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.title}', type='{self.event_type.name}')>"

class EventAttendee(Base):
    __tablename__ = "event_attendees"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EventAttendee(event_id={self.event_id}, user_id={self.user_id})>"

class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    media_id = Column(String)
    media_type = Column(String)
    posted_by = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<News(id={self.id}, title='{self.title}')>"

class Discount(Base):
    __tablename__ = "discounts"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String)
    description = Column(Text)
    location = Column(String)
    validity = Column(String)

    def __repr__(self):
        return f"<Discount(id={self.id}, name='{self.name}')>"

class Podcast(Base):
    __tablename__ = "podcasts"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    audio_file_id = Column(String, nullable=False)
    duration_seconds = Column(Integer)

    def __repr__(self):
        return f"<Podcast(id={self.id}, title='{self.title}')>"

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String, nullable=False) # Telegram file_id
    file_unique_id = Column(String, unique=True)
    file_name = Column(String)
    file_type = Column(String) # MIME type
    category = Column(String, default="general")
    access_level = Column(SAEnum(AccessLevel), default=AccessLevel.PRIVATE, nullable=False)
    gdrive_url = Column(String) # Optional link to Google Drive
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Document(id={self.id}, name='{self.file_name}', user_id={self.user_id})>"

# --- Helper to create tables ---
async def create_db_and_tables():
    """
    Creates all tables in the database.
    This should be called once on application startup.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
