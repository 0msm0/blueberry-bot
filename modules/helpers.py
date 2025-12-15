"""
Helper functions for conversation handlers.

Requires python-telegram-bot v21+
"""
from telegram.ext import ContextTypes

from utils.logger import get_logger

logger = get_logger(__name__)


def clear_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear user_data from context."""
    context.user_data.clear()
    logger.debug("user_data cleared")


def clear_chat_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear chat_data from context."""
    context.chat_data.clear()
    logger.debug("chat_data cleared")


def clear_all_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear both user_data and chat_data."""
    clear_user_data(context)
    clear_chat_data(context)
    logger.debug("All context data cleared")


def get_chat_data(context: ContextTypes.DEFAULT_TYPE, key: str, default=None):
    """Safely get a value from chat_data."""
    return context.chat_data.get(key, default)


def set_chat_data(context: ContextTypes.DEFAULT_TYPE, key: str, value) -> None:
    """Set a value in chat_data."""
    context.chat_data[key] = value


def get_user_data(context: ContextTypes.DEFAULT_TYPE, key: str, default=None):
    """Safely get a value from user_data."""
    return context.user_data.get(key, default)


def set_user_data(context: ContextTypes.DEFAULT_TYPE, key: str, value) -> None:
    """Set a value in user_data."""
    context.user_data[key] = value


def append_to_chat_data_list(context: ContextTypes.DEFAULT_TYPE, key: str, value) -> None:
    """Append a value to a list in chat_data (creates list if doesn't exist)."""
    if key not in context.chat_data:
        context.chat_data[key] = []
    context.chat_data[key].append(value)


# Backwards compatibility aliases
clear_userdata = clear_user_data
clear_chatdata = clear_chat_data
