"""
Database utilities and session management.
Provides cleaner interface for database operations.
"""
from contextlib import contextmanager
from typing import Optional, Type, TypeVar, List, Any
from datetime import datetime

from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy import desc, asc

from utils.logger import get_logger

logger = get_logger(__name__)

# Type variable for generic model operations
T = TypeVar('T')


def get_session() -> SQLAlchemySession:
    """
    Get a new database session.

    Returns:
        SQLAlchemy Session instance
    """
    from dbhelper import Session
    return Session()


@contextmanager
def transaction():
    """
    Context manager for database transactions.

    Automatically commits on success, rolls back on error.

    Usage:
        with transaction() as session:
            user = User(name="test")
            session.add(user)
        # Automatically committed if no exception
    """
    from dbhelper import Session

    session = Session()
    try:
        yield session
        session.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Transaction rolled back due to error: {e}", exc_info=True)
        raise
    finally:
        session.close()


class DatabaseManager:
    """
    Helper class for common database operations.

    Provides a cleaner interface for CRUD operations.
    """

    def __init__(self, session: SQLAlchemySession):
        self.session = session

    def add(self, obj: Any) -> bool:
        """
        Add an object to the session and commit.

        Args:
            obj: SQLAlchemy model instance

        Returns:
            True if successful, False otherwise
        """
        try:
            self.session.add(obj)
            self.session.commit()
            logger.debug(f"Added {type(obj).__name__} to database")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding {type(obj).__name__}: {e}", exc_info=True)
            return False

    def delete(self, obj: Any) -> bool:
        """
        Delete an object from the database.

        Args:
            obj: SQLAlchemy model instance

        Returns:
            True if successful, False otherwise
        """
        try:
            self.session.delete(obj)
            self.session.commit()
            logger.debug(f"Deleted {type(obj).__name__} from database")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting {type(obj).__name__}: {e}", exc_info=True)
            return False

    def update(self) -> bool:
        """
        Commit pending changes to the database.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.session.commit()
            logger.debug("Database updated successfully")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating database: {e}", exc_info=True)
            return False

    def get_by_id(self, model: Type[T], id: int) -> Optional[T]:
        """
        Get a record by its ID.

        Args:
            model: SQLAlchemy model class
            id: Primary key ID

        Returns:
            Model instance or None
        """
        return self.session.query(model).filter(model.id == id).first()

    def get_all(
        self,
        model: Type[T],
        order_by: str = None,
        descending: bool = True,
        limit: int = None
    ) -> List[T]:
        """
        Get all records of a model.

        Args:
            model: SQLAlchemy model class
            order_by: Field name to order by
            descending: If True, order descending
            limit: Maximum number of records

        Returns:
            List of model instances
        """
        query = self.session.query(model)

        if order_by:
            order_col = getattr(model, order_by, None)
            if order_col is not None:
                query = query.order_by(desc(order_col) if descending else asc(order_col))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_user(
        self,
        model: Type[T],
        user_id: int,
        order_by: str = "created_at",
        descending: bool = True,
        limit: int = None
    ) -> List[T]:
        """
        Get all records for a specific user.

        Args:
            model: SQLAlchemy model class
            user_id: User's ID
            order_by: Field name to order by
            descending: If True, order descending
            limit: Maximum number of records

        Returns:
            List of model instances
        """
        query = self.session.query(model).filter(model.user_id == user_id)

        if order_by:
            order_col = getattr(model, order_by, None)
            if order_col is not None:
                query = query.order_by(desc(order_col) if descending else asc(order_col))

        if limit:
            query = query.limit(limit)

        return query.all()

    def count_by_user(self, model: Type[T], user_id: int) -> int:
        """
        Count records for a specific user.

        Args:
            model: SQLAlchemy model class
            user_id: User's ID

        Returns:
            Count of records
        """
        return self.session.query(model).filter(model.user_id == user_id).count()

    def get_latest_by_user(self, model: Type[T], user_id: int) -> Optional[T]:
        """
        Get the most recent record for a user.

        Args:
            model: SQLAlchemy model class
            user_id: User's ID

        Returns:
            Most recent model instance or None
        """
        return (
            self.session.query(model)
            .filter(model.user_id == user_id)
            .order_by(desc(model.created_at))
            .first()
        )


def save_record(session: SQLAlchemySession, record: Any) -> tuple:
    """
    Save a record to the database with proper error handling.

    Args:
        session: Database session
        record: SQLAlchemy model instance to save

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    try:
        session.add(record)
        session.commit()
        logger.info(f"Saved {type(record).__name__}: {record}")
        return True, None
    except Exception as e:
        session.rollback()
        error_msg = f"Error saving {type(record).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def delete_record(session: SQLAlchemySession, record: Any) -> tuple:
    """
    Delete a record from the database with proper error handling.

    Args:
        session: Database session
        record: SQLAlchemy model instance to delete

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    try:
        session.delete(record)
        session.commit()
        logger.info(f"Deleted {type(record).__name__}: {record}")
        return True, None
    except Exception as e:
        session.rollback()
        error_msg = f"Error deleting {type(record).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
