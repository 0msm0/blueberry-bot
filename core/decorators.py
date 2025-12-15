"""
Decorators for common handler patterns.
Reduces boilerplate in conversation handlers.

Requires python-telegram-bot v21+
"""
from functools import wraps
from typing import Callable, Optional
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.logger import get_logger

logger = get_logger(__name__)


def with_session(func: Callable) -> Callable:
    """
    Decorator that provides a database session to the handler.

    The session is passed as a keyword argument 'session'.
    Session is automatically closed after handler completes.

    Usage:
        @with_session
        async def my_handler(update, context, session):
            user = session.query(User).first()
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from dbhelper import Session

        with Session() as session:
            kwargs['session'] = session
            return await func(update, context, *args, **kwargs)

    return wrapper


def require_user(
    register_message: str = "Please /register first to use this feature.",
    return_state: Optional[int] = None
) -> Callable:
    """
    Decorator that ensures user is registered before handler runs.

    If user is not registered, sends register_message and optionally
    returns a conversation state.

    Usage:
        @require_user()
        async def my_handler(update, context, user, session):
            # user is guaranteed to exist here
            pass

        @require_user(return_state=ConversationHandler.END)
        async def conversation_handler(update, context, user, session):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            from dbhelper import Session
            from models import User

            chat_id = update.effective_chat.id

            with Session() as session:
                user = User.get_user_by_chat_id(session, chat_id)

                if not user:
                    logger.info(f"Unregistered user attempted action: {chat_id}")
                    await update.effective_message.reply_text(register_message)

                    if return_state is not None:
                        return return_state
                    return None

                kwargs['user'] = user
                kwargs['session'] = session
                return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def require_timezone(
    timezone_message: str = "Please /set_timezone first before logging activities.",
    return_state: Optional[int] = None
) -> Callable:
    """
    Decorator that ensures user has set timezone before handler runs.

    Automatically includes require_user behavior.

    Usage:
        @require_timezone()
        async def my_handler(update, context, user, session):
            # user exists and has timezone set
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            from dbhelper import Session
            from models import User

            chat_id = update.effective_chat.id

            with Session() as session:
                user = User.get_user_by_chat_id(session, chat_id)

                if not user:
                    logger.info(f"Unregistered user attempted action: {chat_id}")
                    await update.effective_message.reply_text(
                        "Please /register first to use this feature."
                    )
                    if return_state is not None:
                        return return_state
                    return None

                if not user.timezones.count():
                    logger.info(f"User without timezone attempted action: {user.id}")
                    await update.effective_message.reply_text(timezone_message)
                    if return_state is not None:
                        return return_state
                    return None

                kwargs['user'] = user
                kwargs['session'] = session
                return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def log_action(action_name: str) -> Callable:
    """
    Decorator that logs when a handler is called.

    Usage:
        @log_action("food_log")
        async def food_handler(update, context):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            chat_id = update.effective_chat.id if update.effective_chat else "unknown"
            logger.info(f"[{action_name}] Called by chat_id: {chat_id}")

            try:
                result = await func(update, context, *args, **kwargs)
                logger.info(f"[{action_name}] Completed successfully")
                return result
            except Exception as e:
                logger.error(f"[{action_name}] Error: {e}", exc_info=True)
                raise

        return wrapper
    return decorator


def handle_conversation_error(
    error_message: str = "Something went wrong. Please try again.",
    return_state: int = ConversationHandler.END
) -> Callable:
    """
    Decorator that catches exceptions in conversation handlers.

    Usage:
        @handle_conversation_error()
        async def my_handler(update, context):
            # If exception occurs, user sees error_message
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"Conversation error in {func.__name__}: {e}", exc_info=True)

                # Clear any partial data
                context.chat_data.clear()
                context.user_data.clear()

                await update.effective_message.reply_text(error_message)
                return return_state

        return wrapper
    return decorator


def clear_data_on_complete(func: Callable) -> Callable:
    """
    Decorator that clears chat_data after handler completes.

    Useful for conversation end handlers.

    Usage:
        @clear_data_on_complete
        async def save_record(update, context):
            # After this completes, chat_data is cleared
            pass
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        finally:
            context.chat_data.clear()
            logger.debug(f"Cleared chat_data after {func.__name__}")

    return wrapper


def callback_query_handler(func: Callable) -> Callable:
    """
    Decorator that handles common callback query boilerplate.

    Automatically answers the callback query and extracts data.

    Usage:
        @callback_query_handler
        async def handle_selection(update, context, query_data):
            # query_data contains the callback_data
            pass
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        query = update.callback_query
        await query.answer()

        kwargs['query_data'] = query.data.strip()
        return await func(update, context, *args, **kwargs)

    return wrapper
