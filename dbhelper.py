"""
Database configuration and session management.

Uses PostgreSQL for both development and production.
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseConfig:
    """Database configuration container."""

    def __init__(self):
        # PostgreSQL configuration
        self.pg_host = os.environ.get("DB_HOST", "localhost")
        self.pg_user = os.environ.get("DB_USER", "postgres")
        self.pg_password = os.environ.get("DB_PASSWORD", "")
        self.pg_database = os.environ.get("DB_NAME", "blueberry_bot")
        self.pg_port = os.environ.get("DB_PORT", "5432")

        # Optional: Full database URL (overrides individual settings)
        self.database_url_override = os.environ.get("DATABASE_URL")

    @property
    def database_url(self) -> str:
        """Get the database URL."""
        # Use DATABASE_URL if provided (common in cloud deployments)
        if self.database_url_override:
            url = self.database_url_override
            # Handle Heroku-style postgres:// URLs (need postgresql://)
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url

        return (
            f"postgresql://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        )

    @property
    def engine_kwargs(self) -> dict:
        """Get engine configuration."""
        return {
            "pool_recycle": 300,
            "pool_pre_ping": True,  # Verify connections before use
            "pool_size": 5,
            "max_overflow": 10,
            "echo": os.environ.get("DB_ECHO", "").lower() == "true",
        }


# Initialize configuration
config = DatabaseConfig()

# Create engine
engine = create_engine(config.database_url, **config.engine_kwargs)

# Create session factory
session_factory = sessionmaker(bind=engine)

# Create scoped session for thread safety
Session = scoped_session(session_factory)

# Create declarative base for models
Base = declarative_base()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.

    Automatically handles commit/rollback and session cleanup.

    Usage:
        with get_db_session() as session:
            user = session.query(User).first()
            # Session auto-commits on success, rollbacks on exception
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database():
    """
    Initialize database tables.

    Creates all tables defined by models that inherit from Base.
    Safe to call multiple times (uses checkfirst=True).
    """
    from models import (
        User, Timezone, Wakesleep, Food, Water, Gym,
        Yoga, Pranayam, Thought, Task,
        Gratitude, ThemeOfTheDay, SelfLove, Affirmation, UserSettings,
        AffirmationCategory, AffirmationListItem, Goal
    )

    # Create tables in order (respecting foreign key dependencies)
    tables = [
        User.__table__,
        Timezone.__table__,
        Wakesleep.__table__,
        Food.__table__,
        Water.__table__,
        Gym.__table__,
        Yoga.__table__,
        Pranayam.__table__,
        Thought.__table__,
        Task.__table__,
        Gratitude.__table__,
        ThemeOfTheDay.__table__,
        SelfLove.__table__,
        Affirmation.__table__,
        UserSettings.__table__,
        AffirmationCategory.__table__,
        AffirmationListItem.__table__,
        Goal.__table__,
    ]

    for table in tables:
        table.create(engine, checkfirst=True)


def get_engine():
    """Get the SQLAlchemy engine instance."""
    return engine


def close_all_sessions():
    """Close all sessions (useful for cleanup)."""
    Session.remove()
