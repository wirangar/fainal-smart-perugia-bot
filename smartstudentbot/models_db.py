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
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
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
    user_id = Column(BigInteger, ForeignKey("users.user_id"), unique=True, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    budget_min = Column(Integer)
    budget_max = Column(Integer)
    location_preferences = Column(Text) # Comma-separated list of neighborhoods
    habits = Column(Text) # e.g., "non-smoker, quiet, tidy"
    about_me = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<RoommateProfile(user_id={self.user_id}, is_active={self.is_active})>"

# --- Helper to create tables ---
async def create_db_and_tables():
    """
    Creates all tables in the database.
    This should be called once on application startup.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
