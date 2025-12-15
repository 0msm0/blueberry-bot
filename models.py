"""
Database models for the wellness tracking bot.

All models inherit from BaseModel which provides common fields and methods.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Text, Date, desc, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from dbhelper import Base

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class BaseModel:
    """
    Base mixin class providing common fields and methods for all models.
    """
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    @classmethod
    def get_by_id(cls, session: "Session", id: int) -> Optional["BaseModel"]:
        """Get a record by its primary key."""
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_all_by_user_id(cls, session: "Session", user_id: int, limit: int = None) -> List["BaseModel"]:
        """Get all records for a user, ordered by created_at descending."""
        query = session.query(cls).filter(cls.user_id == user_id).order_by(desc(cls.created_at))
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_latest_by_user_id(cls, session: "Session", user_id: int) -> Optional["BaseModel"]:
        """Get the most recent record for a user."""
        return (
            session.query(cls)
            .filter(cls.user_id == user_id)
            .order_by(desc(cls.created_at))
            .first()
        )

    @classmethod
    def count_by_user_id(cls, session: "Session", user_id: int) -> int:
        """Count records for a user."""
        return session.query(cls).filter(cls.user_id == user_id).count()


class User(Base):
    """User model - stores registered users."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False, unique=True, index=True)
    tg_username = Column(String(255), nullable=True, unique=True)
    name = Column(String(255), nullable=False)
    email_id = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Relationships
    timezones = relationship("Timezone", back_populates="user", lazy="dynamic")
    wakesleeps = relationship("Wakesleep", back_populates="user", lazy="dynamic")
    foods = relationship("Food", back_populates="user", lazy="dynamic")
    waters = relationship("Water", back_populates="user", lazy="dynamic")
    gyms = relationship("Gym", back_populates="user", lazy="dynamic")
    yogas = relationship("Yoga", back_populates="user", lazy="dynamic")
    pranayams = relationship("Pranayam", back_populates="user", lazy="dynamic")
    thoughts = relationship("Thought", back_populates="user", lazy="dynamic")
    tasks = relationship("Task", back_populates="user", lazy="dynamic")
    gratitudes = relationship("Gratitude", back_populates="user", lazy="dynamic")
    themes_of_the_day = relationship("ThemeOfTheDay", back_populates="user", lazy="dynamic")
    self_loves = relationship("SelfLove", back_populates="user", lazy="dynamic")
    affirmations = relationship("Affirmation", back_populates="user", lazy="dynamic")
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    affirmation_categories = relationship("AffirmationCategory", back_populates="user", lazy="dynamic")
    affirmation_lists = relationship("AffirmationListItem", back_populates="user", lazy="dynamic")
    goals = relationship("Goal", back_populates="user", lazy="dynamic")

    @classmethod
    def get_by_id(cls, session: "Session", id: int) -> Optional["User"]:
        """Get user by ID."""
        return session.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_user_by_chat_id(cls, session: "Session", chat_id: int) -> Optional["User"]:
        """Get user by Telegram chat ID."""
        return session.query(cls).filter(cls.chat_id == chat_id).first()

    @classmethod
    def get_by_email(cls, session: "Session", email: str) -> Optional["User"]:
        """Get user by email address."""
        return session.query(cls).filter(cls.email_id == email).first()

    @classmethod
    def get_all(cls, session: "Session") -> List["User"]:
        """Get all users."""
        return session.query(cls).all()

    def get_current_timezone(self) -> Optional["Timezone"]:
        """Get the user's most recent timezone setting."""
        return self.timezones.order_by(desc(Timezone.created_at)).first()

    def __repr__(self):
        return f"<User(id={self.id}, chat_id={self.chat_id}, name='{self.name}')>"


class Timezone(Base):
    """Timezone model - tracks user timezone settings over time."""
    __tablename__ = 'timezones'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    timezone_name = Column(String(255), nullable=False)
    timezone_offset = Column(String(255), nullable=False)
    effective_from = Column(Date, nullable=False, default=datetime.now)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="timezones")

    @classmethod
    def get_by_user_id(cls, session: "Session", user_id: int) -> Optional["Timezone"]:
        """Get the most recent timezone for a user."""
        return (
            session.query(cls)
            .filter(cls.user_id == user_id)
            .order_by(desc(cls.created_at))
            .first()
        )

    def __repr__(self):
        return f"<Timezone(id={self.id}, user_id={self.user_id}, name='{self.timezone_name}')>"


class Wakesleep(Base, BaseModel):
    """Sleep/wake tracking model."""
    __tablename__ = 'wakesleeps'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    sleeptime = Column(DateTime, nullable=False)
    wakeuptime = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="wakesleeps")

    @property
    def duration_minutes(self) -> int:
        """Calculate sleep duration in minutes."""
        if self.sleeptime and self.wakeuptime:
            delta = self.wakeuptime - self.sleeptime
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string."""
        minutes = self.duration_minutes
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"

    def __repr__(self):
        return f"<Wakesleep(id={self.id}, user_id={self.user_id}, sleep={self.sleeptime}, wake={self.wakeuptime})>"


class Food(Base, BaseModel):
    """Food logging model."""
    __tablename__ = 'foods'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    food_item = Column(Text, nullable=False)
    food_label = Column(String(100), nullable=False)
    food_time = Column(DateTime, nullable=False)
    food_photos = Column(Text, nullable=True)
    food_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="foods")

    @property
    def items_list(self) -> List[str]:
        """Get food items as a list."""
        if self.food_item:
            return self.food_item.split(",,,")
        return []

    @property
    def photos_list(self) -> List[str]:
        """Get photos as a list."""
        if self.food_photos:
            return self.food_photos.split(",,,")
        return []

    def __repr__(self):
        return f"<Food(id={self.id}, user_id={self.user_id}, label='{self.food_label}', time={self.food_time})>"


class Water(Base, BaseModel):
    """Water intake tracking model."""
    __tablename__ = 'waters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    water_time = Column(DateTime, nullable=False)
    amount_ml = Column(Integer, nullable=False)
    water_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="waters")

    @property
    def amount_glasses(self) -> float:
        """Get amount in glasses (1 glass = 250ml)."""
        return self.amount_ml / 250

    def __repr__(self):
        return f"<Water(id={self.id}, user_id={self.user_id}, amount={self.amount_ml}ml, time={self.water_time})>"


class Gym(Base, BaseModel):
    """Gym workout tracking model."""
    __tablename__ = 'gyms'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    gym_datetime = Column(DateTime, nullable=False)
    gym_type = Column(String(255), nullable=False)
    total_set = Column(Integer, nullable=False)
    repetition = Column(String(255), nullable=False)  # Comma-separated values per set
    weight = Column(String(255), nullable=False)  # Comma-separated values per set
    gym_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="gyms")

    @property
    def reps_list(self) -> List[str]:
        """Get reps as a list."""
        if self.repetition:
            return [r.strip() for r in self.repetition.split(",")]
        return []

    @property
    def weights_list(self) -> List[str]:
        """Get weights as a list."""
        if self.weight:
            return [w.strip() for w in self.weight.split(",")]
        return []

    def get_sets_formatted(self) -> str:
        """Get formatted string showing all sets."""
        reps = self.reps_list
        weights = self.weights_list
        lines = []
        for i, (r, w) in enumerate(zip(reps, weights), 1):
            lines.append(f"Set {i}: {w}kg x {r} reps")
        return "\n".join(lines)

    def __repr__(self):
        return f"<Gym(id={self.id}, user_id={self.user_id}, type='{self.gym_type}', sets={self.total_set})>"


class Yoga(Base, BaseModel):
    """Yoga session tracking model."""
    __tablename__ = 'yogas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    yoga_type = Column(String(255), nullable=False)
    yoga_datetime = Column(DateTime, nullable=False)
    repetition = Column(Integer, nullable=False)
    yoga_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="yogas")

    def __repr__(self):
        return f"<Yoga(id={self.id}, user_id={self.user_id}, type='{self.yoga_type}', reps={self.repetition})>"


class Pranayam(Base, BaseModel):
    """Pranayam (breathing exercise) tracking model."""
    __tablename__ = 'pranayams'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    pranayam_type = Column(String(255), nullable=False)
    pranayam_datetime = Column(DateTime, nullable=False)
    repetition = Column(Integer, nullable=False)
    pranayam_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="pranayams")

    def __repr__(self):
        return f"<Pranayam(id={self.id}, user_id={self.user_id}, type='{self.pranayam_type}', reps={self.repetition})>"


class Thought(Base, BaseModel):
    """Thoughts/journaling model."""
    __tablename__ = 'thoughts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Renamed from 'thoughts' for clarity
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="thoughts")

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Thought(id={self.id}, user_id={self.user_id}, content='{preview}')>"


class Task(Base, BaseModel):
    """Completed tasks tracking model."""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Renamed from 'tasks' for clarity
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="tasks")

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Task(id={self.id}, user_id={self.user_id}, content='{preview}')>"


class DailyReflectionBase:
    """
    Base mixin for daily reflection models (gratitude, theme, selflove, affirmation).
    Provides common fields and methods.
    """
    @classmethod
    def get_for_date(cls, session: "Session", user_id: int, prompt_date) -> Optional["DailyReflectionBase"]:
        """Get response for a specific date."""
        return (
            session.query(cls)
            .filter(cls.user_id == user_id)
            .filter(cls.prompt_date == prompt_date)
            .first()
        )

    @classmethod
    def exists_for_date(cls, session: "Session", user_id: int, prompt_date) -> bool:
        """Check if response exists for date."""
        return cls.get_for_date(session, user_id, prompt_date) is not None

    @property
    def content_list(self) -> List[str]:
        """Get content items as a list."""
        if self.content:
            return self.content.split(",,,")
        return []


class Gratitude(Base, BaseModel, DailyReflectionBase):
    """Daily gratitude entries."""
    __tablename__ = 'gratitudes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    prompt_date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)  # Items joined with ,,,
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="gratitudes")

    def __repr__(self):
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<Gratitude(id={self.id}, user_id={self.user_id}, date={self.prompt_date})>"


class ThemeOfTheDay(Base, BaseModel, DailyReflectionBase):
    """Daily theme/intention entries."""
    __tablename__ = 'themes_of_the_day'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    prompt_date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)  # Single theme
    reminder_count = Column(Integer, nullable=False, default=0)  # Reminders sent today
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="themes_of_the_day")

    def __repr__(self):
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<ThemeOfTheDay(id={self.id}, user_id={self.user_id}, date={self.prompt_date})>"


class SelfLove(Base, BaseModel, DailyReflectionBase):
    """Daily self-love entries."""
    __tablename__ = 'self_loves'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    prompt_date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)  # Items joined with ,,,
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="self_loves")

    def __repr__(self):
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<SelfLove(id={self.id}, user_id={self.user_id}, date={self.prompt_date})>"


class Affirmation(Base, BaseModel, DailyReflectionBase):
    """Daily affirmation entries."""
    __tablename__ = 'affirmations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    prompt_date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)  # Items joined with ,,,
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="affirmations")

    def __repr__(self):
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<Affirmation(id={self.id}, user_id={self.user_id}, date={self.prompt_date})>"


class UserSettings(Base):
    """User settings for notifications and preferences."""
    __tablename__ = 'user_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True, index=True)

    # Daily prompt schedule times (stored as "HH:MM" strings)
    gratitude_time = Column(String(5), nullable=False, default="07:00")
    themeoftheday_time = Column(String(5), nullable=False, default="07:30")
    affirmation_time = Column(String(5), nullable=False, default="08:00")
    selflove_time = Column(String(5), nullable=False, default="21:00")

    # Enable/disable scheduled prompts
    gratitude_enabled = Column(Integer, nullable=False, default=1)  # 1=enabled, 0=disabled
    themeoftheday_enabled = Column(Integer, nullable=False, default=1)
    affirmation_enabled = Column(Integer, nullable=False, default=1)
    selflove_enabled = Column(Integer, nullable=False, default=1)

    # Theme reminders (3 times per day after theme is set)
    theme_reminders_enabled = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="settings")

    @classmethod
    def get_or_create(cls, session: "Session", user_id: int) -> "UserSettings":
        """Get existing settings or create default ones."""
        settings = session.query(cls).filter(cls.user_id == user_id).first()
        if not settings:
            settings = cls(user_id=user_id)
            session.add(settings)
            session.commit()
        return settings

    def get_schedule_dict(self) -> dict:
        """Get schedule as a dictionary."""
        return {
            'gratitude': {'time': self.gratitude_time, 'enabled': bool(self.gratitude_enabled)},
            'themeoftheday': {'time': self.themeoftheday_time, 'enabled': bool(self.themeoftheday_enabled)},
            'affirmation': {'time': self.affirmation_time, 'enabled': bool(self.affirmation_enabled)},
            'selflove': {'time': self.selflove_time, 'enabled': bool(self.selflove_enabled)},
        }

    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id})>"


class AffirmationCategory(Base, BaseModel):
    """User's affirmation categories (predefined + custom)."""
    __tablename__ = 'affirmation_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "self-love", "gratitude"
    display_name = Column(String(100), nullable=False)  # e.g., "Self-Love", "Gratitude"
    is_predefined = Column(Integer, nullable=False, default=0)  # 1=predefined, 0=custom
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="affirmation_categories")
    lists = relationship("AffirmationListItem", back_populates="category", cascade="all, delete-orphan")

    # Predefined categories
    PREDEFINED = [
        ("self-love", "Self-Love"),
        ("gratitude", "Gratitude"),
        ("paradigm-shifting", "Paradigm-Shifting"),
    ]

    @classmethod
    def get_by_user_and_name(cls, session: "Session", user_id: int, name: str) -> Optional["AffirmationCategory"]:
        """Get category by user and name."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.name == name
        ).first()

    @classmethod
    def get_all_for_user(cls, session: "Session", user_id: int) -> List["AffirmationCategory"]:
        """Get all categories for user (predefined first, then custom alphabetically)."""
        return session.query(cls).filter(cls.user_id == user_id).order_by(
            desc(cls.is_predefined), cls.display_name
        ).all()

    @classmethod
    def create_predefined_for_user(cls, session: "Session", user_id: int) -> None:
        """Create predefined categories for a new user."""
        for name, display in cls.PREDEFINED:
            existing = cls.get_by_user_and_name(session, user_id, name)
            if not existing:
                category = cls(
                    user_id=user_id,
                    name=name,
                    display_name=display,
                    is_predefined=1
                )
                session.add(category)

    def __repr__(self):
        return f"<AffirmationCategory(id={self.id}, user_id={self.user_id}, name='{self.name}')>"


class AffirmationListItem(Base, BaseModel):
    """Individual affirmation lists within a category."""
    __tablename__ = 'affirmation_lists'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('affirmation_categories.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)  # List name/title
    items = Column(Text, nullable=False)  # Affirmations joined with ,,,
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="affirmation_lists")
    category = relationship("AffirmationCategory", back_populates="lists")

    @property
    def items_list(self) -> List[str]:
        """Get items as a list."""
        if self.items:
            return self.items.split(",,,")
        return []

    @classmethod
    def get_by_category(cls, session: "Session", category_id: int) -> List["AffirmationListItem"]:
        """Get all lists in a category."""
        return session.query(cls).filter(cls.category_id == category_id).order_by(cls.title).all()

    @classmethod
    def get_by_id_and_user(cls, session: "Session", list_id: int, user_id: int) -> Optional["AffirmationListItem"]:
        """Get a specific list by ID, ensuring it belongs to the user."""
        return session.query(cls).filter(cls.id == list_id, cls.user_id == user_id).first()

    def __repr__(self):
        return f"<AffirmationListItem(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class Goal(Base):
    """User's wellness goals/north star for different areas."""
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    area = Column(String(50), nullable=False, index=True)  # sleep, food, gym, yoga, pranayam
    goal_text = Column(Text, nullable=False)  # The actual goal description
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # Ensure only one goal per user per area
    __table_args__ = (
        UniqueConstraint('user_id', 'area', name='uq_user_goal_area'),
    )

    user = relationship("User", back_populates="goals")

    # Predefined areas with display names
    AREAS = [
        ('sleep', 'Sleep'),
        ('food', 'Food/Diet'),
        ('gym', 'Gym/Exercise'),
        ('yoga', 'Yoga'),
        ('pranayam', 'Pranayam'),
    ]

    @classmethod
    def get_by_user_and_area(cls, session: "Session", user_id: int, area: str) -> Optional["Goal"]:
        """Get goal for a specific area."""
        return session.query(cls).filter(
            cls.user_id == user_id,
            cls.area == area
        ).first()

    @classmethod
    def get_all_for_user(cls, session: "Session", user_id: int) -> List["Goal"]:
        """Get all goals for a user."""
        return session.query(cls).filter(cls.user_id == user_id).all()

    @classmethod
    def set_goal(cls, session: "Session", user_id: int, area: str, goal_text: str) -> "Goal":
        """Set or update a goal for an area."""
        existing = cls.get_by_user_and_area(session, user_id, area)
        if existing:
            existing.goal_text = goal_text
            existing.updated_at = datetime.now()
            return existing
        else:
            goal = cls(user_id=user_id, area=area, goal_text=goal_text)
            session.add(goal)
            return goal

    @classmethod
    def delete_goal(cls, session: "Session", user_id: int, area: str) -> bool:
        """Delete a goal for an area. Returns True if deleted."""
        existing = cls.get_by_user_and_area(session, user_id, area)
        if existing:
            session.delete(existing)
            return True
        return False

    def __repr__(self):
        preview = self.goal_text[:30] + "..." if len(self.goal_text) > 30 else self.goal_text
        return f"<Goal(id={self.id}, user_id={self.user_id}, area='{self.area}')>"


# Backwards compatibility aliases (for existing code during migration)
Thoughts = Thought
Taskcompleted = Task
