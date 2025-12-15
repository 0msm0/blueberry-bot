"""
Timezone setting conversation handler.

Requires python-telegram-bot v21+
"""
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from sqlalchemy import desc

from dbhelper import Session
from models import User, Timezone
from utils.logger import get_logger
from utils.keyboards import generate_options_keyboard, make_markup
from utils.patterns import TIMEZONE_NAME_PATTERN, TIMEZONE_EFFECTIVE_PATTERN
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_user_data

logger = get_logger(__name__)

# Conversation states
COUNTRY, TIMEZONE_NAME, EFFECTIVE_FROM = range(3)

# Configuration
TIMEOUT_SECONDS = 300  # 5 minutes

# Timezone data
TIMEZONE_DATA = {
    "Asia/Kolkata": {"country": "India", "offset": "+5:30"},
    "Europe/London": {"country": "UK", "offset": "+0:00"},
    "Pacific/Honolulu": {"country": "US", "offset": "-10:00"},
    "America/Anchorage": {"country": "US", "offset": "-9:00"},
    "America/Los_Angeles": {"country": "US", "offset": "-8:00"},
    "America/Denver": {"country": "US", "offset": "-7:00"},
    "America/Chicago": {"country": "US", "offset": "-6:00"},
    "America/New_York": {"country": "US", "offset": "-5:00"},
}

# Country aliases
COUNTRY_ALIASES = {
    "india": "india",
    "uk": "uk",
    "united kingdom": "uk",
    "great britain": "uk",
    "britain": "uk",
    "us": "us",
    "usa": "us",
    "united states": "us",
    "united states of america": "us",
    "america": "us",
}


def get_timezone_keyboard(country: str):
    """Generate timezone keyboard for a specific country."""
    if country == "india":
        options = [("Asia/Kolkata (IST)", "Asia/Kolkata")]
    elif country == "uk":
        options = [("Europe/London (GMT/BST)", "Europe/London")]
    elif country == "us":
        options = [
            ("Hawaii", "Pacific/Honolulu"),
            ("Alaska", "America/Anchorage"),
            ("Pacific", "America/Los_Angeles"),
            ("Mountain", "America/Denver"),
            ("Central", "America/Chicago"),
            ("Eastern", "America/New_York"),
        ]
    else:
        return None

    return generate_options_keyboard(options, columns=2)


async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for timezone setting."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

    await update.effective_message.reply_text(
        "Let's set your timezone.\n\n"
        "Which country do you live in?\n"
        "(Currently supported: India, UK, US)\n\n"
        "Use /cancel to cancel."
    )
    return COUNTRY


async def handle_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country input."""
    country_input = update.effective_message.text.strip().lower()

    country = COUNTRY_ALIASES.get(country_input)

    if not country:
        await update.effective_message.reply_text(
            "Sorry, we currently support only India, UK, and US.\n\n"
            "Please enter one of these countries:"
        )
        return COUNTRY

    context.user_data['country'] = country

    keyboard = get_timezone_keyboard(country)
    if keyboard:
        await update.effective_message.reply_text(
            "Select your timezone:",
            reply_markup=make_markup(keyboard)
        )
        return TIMEZONE_NAME
    else:
        await update.effective_message.reply_text(
            "Error getting timezones. Please try again with /set_timezone"
        )
        return ConversationHandler.END


async def handle_timezone_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone selection."""
    query = update.callback_query
    await query.answer()

    tz_name = query.data
    tz_data = TIMEZONE_DATA.get(tz_name)

    if not tz_data:
        await query.edit_message_text("Invalid timezone. Please try again with /set_timezone")
        return ConversationHandler.END

    context.user_data['timezone_name'] = tz_name
    context.user_data['timezone_offset'] = tz_data['offset']

    effective_options = [
        ("Since Registration", "sincefirstday"),
        ("Yesterday", "yesterday"),
        ("Today", "today"),
    ]
    keyboard = generate_options_keyboard(effective_options, columns=3)

    await query.edit_message_text(
        f"Timezone: {tz_name}\n\n"
        "Since when should this timezone be effective?",
        reply_markup=make_markup(keyboard)
    )
    return EFFECTIVE_FROM


async def handle_effective_from(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle effective from selection and save timezone."""
    query = update.callback_query
    await query.answer()

    selection = query.data
    context.user_data['effective_selection'] = selection

    return await save_timezone(update, context)


async def save_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save timezone to database."""
    chat_id = update.effective_chat.id
    user_data = context.user_data
    today = datetime.today().date()

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Error: User not found. Please /register first.")
            clear_user_data(context)
            return ConversationHandler.END

        # Determine effective date
        selection = user_data.get('effective_selection', 'today')
        if selection == 'sincefirstday':
            effective_date = user.created_at.date()
        elif selection == 'yesterday':
            effective_date = today - timedelta(days=1)
        else:
            effective_date = today

        timezone = Timezone(
            user_id=user.id,
            timezone_name=user_data['timezone_name'],
            timezone_offset=user_data['timezone_offset'],
            effective_from=effective_date,
            created_at=datetime.now()
        )

        try:
            session.add(timezone)
            session.commit()

            logger.info(f"Timezone saved for user {user.id}: {timezone}")

            # Delete the selection message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"Timezone set successfully!\n\n"
                    f"<b>Timezone:</b> {timezone.timezone_name}\n"
                    f"<b>Offset:</b> {timezone.timezone_offset}\n"
                    f"<b>Effective from:</b> {timezone.effective_from}\n\n"
                    f"You're all set! Use /sleep or /food to start logging.",
                    parse_mode="HTML"
                )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving timezone: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Error saving timezone. Please try again with /set_timezone"
            )
        finally:
            clear_user_data(context)

    return ConversationHandler.END


async def my_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's timezone history."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return

        if user.timezones.count():
            messages = []
            for tz in user.timezones.order_by(desc(Timezone.created_at)).all():
                messages.append(
                    f"<b>{tz.timezone_name}</b> (since {tz.effective_from})"
                )
            await update.effective_message.reply_text(
                "Your timezone settings:\n\n" + "\n".join(messages),
                parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                "You haven't set a timezone yet. Use /set_timezone to set one."
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel timezone setting."""
    logger.info("Timezone setting cancelled")
    clear_user_data(context)
    await update.effective_message.reply_text("Timezone setting cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Timezone setting timed out")
    clear_user_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Timezone setting timed out. Please use /set_timezone to try again."
        )
    return ConversationHandler.END


# Build the conversation handler
set_timezone_handler = ConversationHandler(
    entry_points=[CommandHandler('set_timezone', set_timezone)],
    states={
        COUNTRY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country)
        ],
        TIMEZONE_NAME: [
            CallbackQueryHandler(handle_timezone_selection, pattern=TIMEZONE_NAME_PATTERN)
        ],
        EFFECTIVE_FROM: [
            CallbackQueryHandler(handle_effective_from, pattern=TIMEZONE_EFFECTIVE_PATTERN)
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('cancel_timezone', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)

# Export for main.py
mytimezone = my_timezone
