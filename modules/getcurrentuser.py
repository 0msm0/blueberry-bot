"""
User retrieval helper for handlers.

Requires python-telegram-bot v21+
"""
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from models import User
from utils.logger import get_logger

logger = get_logger(__name__)


async def get_current_user(
    chat_id: int,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session,
    require_registration: bool = True
) -> Optional[User]:
    """
    Get current user from database.

    Args:
        chat_id: Telegram chat ID
        update: Telegram Update object
        context: Callback context
        session: Database session
        require_registration: If True, sends message when user not found

    Returns:
        User instance if found, None otherwise
    """
    user = User.get_user_by_chat_id(session=session, chat_id=chat_id)

    if user:
        # Store in context for potential future use
        context.user_data['user'] = user
        logger.debug(f"Retrieved user: {user.id}")
        return user
    else:
        logger.info(f"User not found for chat_id: {chat_id}")
        if require_registration:
            await update.effective_message.reply_text("Please /register first to use this feature.")
        return None


async def get_user_with_timezone(
    chat_id: int,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session,
) -> Optional[User]:
    """
    Get current user and verify they have a timezone set.

    Args:
        chat_id: Telegram chat ID
        update: Telegram Update object
        context: Callback context
        session: Database session

    Returns:
        User instance if found and has timezone, None otherwise
    """
    user = await get_current_user(chat_id, update, context, session)

    if not user:
        return None

    if not user.timezones.count():
        logger.info(f"User {user.id} has no timezone set")
        await update.effective_message.reply_text(
            "Please /set_timezone first before logging activities."
        )
        return None

    return user
