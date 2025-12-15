"""
User registration conversation handler.

Requires python-telegram-bot v21+
"""
from datetime import datetime

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from dbhelper import Session
from models import User
from utils.logger import get_logger
from utils.validators import validate_email, validate_name
from utils.formatters import mask_email
from utils.ratelimit import rate_limit
from modules.helpers import clear_user_data

logger = get_logger(__name__)

# Conversation states
NAME, EMAIL = range(2)

# Configuration
TIMEOUT_SECONDS = 60


@rate_limit(max_calls=3, period_seconds=60, message="Too many registration attempts. Please wait a minute.")
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for registration conversation."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        existing_user = User.get_user_by_chat_id(session, chat_id)

        if existing_user:
            logger.info(f"User already registered: {chat_id}")
            await update.effective_message.reply_text(
                f"You are already registered with the following details:\n\n"
                f"<b>Name:</b> {existing_user.name}\n"
                f"<b>Email:</b> {existing_user.email_id}",
                parse_mode="HTML"
            )
            return ConversationHandler.END

    logger.info(f"Starting registration for chat_id: {chat_id}")
    await update.effective_message.reply_text(
        "Let's get you registered.\n\n"
        "What's your name?\n\n"
        "(Use /cancel to cancel registration)"
    )
    return NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input."""
    name = update.effective_message.text.strip()

    is_valid, error_msg = validate_name(name)
    if not is_valid:
        await update.effective_message.reply_text(f"{error_msg}\n\nPlease enter your name:")
        return NAME

    context.user_data['name'] = name
    context.user_data['chat_id'] = update.effective_message.chat_id

    logger.info(f"Registration - Name received: {name}")
    await update.effective_message.reply_text(
        f"Nice to meet you, {name}!\n\nNow please enter your email address:"
    )
    return EMAIL


async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email input."""
    email = update.effective_message.text.strip().lower()

    is_valid, error_msg = validate_email(email)
    if not is_valid:
        await update.effective_message.reply_text(f"{error_msg}\n\nPlease enter a valid email:")
        return EMAIL

    # Check if email already exists
    with Session() as session:
        existing = User.get_by_email(session, email)
        if existing:
            await update.effective_message.reply_text(
                "This email is already registered.\n\nPlease enter a different email:"
            )
            logger.info(f"Registration - Duplicate email attempted: {mask_email(email)}")
            return EMAIL

    context.user_data['email'] = email
    logger.info(f"Registration - Email received: {mask_email(email)}")

    # Save user
    return await save_user(update, context)


async def handle_invalid_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle invalid email format."""
    logger.info("Registration - Invalid email format received")
    await update.effective_message.reply_text(
        "That doesn't look like a valid email address.\n\n"
        "Please enter a valid email (e.g., name@example.com):"
    )
    return EMAIL


async def save_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save user to database."""
    user_data = context.user_data
    tg_username = update.effective_message.from_user.username

    user = User(
        chat_id=user_data['chat_id'],
        tg_username=tg_username,
        name=user_data['name'],
        email_id=user_data['email'],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    with Session() as session:
        try:
            session.add(user)
            session.commit()

            logger.info(f"User registered successfully: chat_id={user.chat_id}, name={user.name}")
            await update.effective_message.reply_text(
                f"Awesome! You're registered.\n\n"
                f"<b>Name:</b> {user.name}\n"
                f"<b>Email:</b> {user.email_id}\n\n"
                f"Next, use /set_timezone so we can store your logs in your local time.",
                parse_mode="HTML"
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving user: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Something went wrong during registration. Please try again with /register"
            )
        finally:
            clear_user_data(context)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel registration."""
    logger.info("Registration cancelled")
    clear_user_data(context)
    await update.effective_message.reply_text("Registration cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Registration timed out")
    clear_user_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"Registration timed out. Please use /register to start again."
        )
    return ConversationHandler.END


# Email regex pattern
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Build the conversation handler
registration_handler = ConversationHandler(
    entry_points=[CommandHandler('register', register)],
    states={
        NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
        ],
        EMAIL: [
            MessageHandler(filters.Regex(EMAIL_REGEX), handle_email),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_email)
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('reg_cancel', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)
