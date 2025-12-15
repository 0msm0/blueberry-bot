"""
Rate limiting decorator for bot commands.

Prevents abuse by limiting how often users can invoke commands.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import get_logger

logger = get_logger(__name__)

# Store for rate limit tracking: {user_id: [(timestamp, command), ...]}
_rate_limit_store: dict = defaultdict(list)


def rate_limit(
    max_calls: int = 10,
    period_seconds: int = 60,
    message: Optional[str] = None
) -> Callable:
    """
    Rate limiting decorator for bot command handlers.

    Args:
        max_calls: Maximum number of calls allowed in the period
        period_seconds: Time period in seconds
        message: Custom message to send when rate limited

    Returns:
        Decorated function

    Usage:
        @rate_limit(max_calls=5, period_seconds=60)
        async def my_command(update, context):
            ...
    """
    default_message = (
        f"Too many requests. Please wait before trying again."
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id if update.effective_user else None

            if user_id is None:
                return await func(update, context, *args, **kwargs)

            now = datetime.now()
            cutoff = now - timedelta(seconds=period_seconds)

            # Clean old entries for this user
            _rate_limit_store[user_id] = [
                (ts, cmd) for ts, cmd in _rate_limit_store[user_id]
                if ts > cutoff
            ]

            # Check if rate limited
            recent_calls = len(_rate_limit_store[user_id])
            if recent_calls >= max_calls:
                logger.warning(
                    f"[User:{user_id}] Rate limited for {func.__name__} "
                    f"({recent_calls}/{max_calls} in {period_seconds}s)"
                )
                if update.effective_message:
                    await update.effective_message.reply_text(message or default_message)
                return None

            # Record this call
            _rate_limit_store[user_id].append((now, func.__name__))

            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def clear_rate_limit_store():
    """Clear all rate limit data (useful for testing)."""
    _rate_limit_store.clear()


def get_user_rate_limit_status(user_id: int, period_seconds: int = 60) -> tuple:
    """
    Get rate limit status for a user.

    Args:
        user_id: User ID to check
        period_seconds: Time period to check

    Returns:
        Tuple of (calls_in_period, oldest_call_age_seconds)
    """
    now = datetime.now()
    cutoff = now - timedelta(seconds=period_seconds)

    recent = [ts for ts, _ in _rate_limit_store.get(user_id, []) if ts > cutoff]

    if not recent:
        return 0, None

    oldest_age = (now - min(recent)).total_seconds()
    return len(recent), oldest_age
