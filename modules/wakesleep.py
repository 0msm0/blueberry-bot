"""
Sleep/wake tracking conversation handler.

Requires python-telegram-bot v21+
"""
from datetime import datetime

from telegram import Update
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
from models import User, Wakesleep
from utils.logger import get_logger
from utils.keyboards import (
    generate_date_keyboard,
    generate_hour_keyboard,
    generate_minute_keyboard,
    make_markup,
    DATE_KEYBOARD,
    DATE_KEYBOARD_WITH_NOW,
    HOUR_KEYBOARD,
    HOUR_KEYBOARD_WITH_NOW,
)
from utils.patterns import DATE_PATTERN, HOUR_PATTERN, MINUTE_PATTERN
from utils.formatters import (
    readable_datetime,
    parse_date_selection,
    parse_custom_date,
    combine_date_time,
    format_duration,
)
from modules.getcurrentuser import get_user_with_timezone
from modules.helpers import clear_chat_data

logger = get_logger(__name__)

# Conversation states
SLEEP_DATE, SLEEP_HOUR, SLEEP_MINUTE = range(3)
WAKE_DATE, WAKE_HOUR, WAKE_MINUTE = range(3, 6)
NOTES = 6
CUSTOM_SLEEP_DATE = 7
CUSTOM_WAKE_DATE = 8

# Configuration
TIMEOUT_SECONDS = 600  # 10 minutes


async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for sleep/wake logging."""
    chat_id = update.message.chat_id

    with Session() as session:
        user = await get_user_with_timezone(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

    context.chat_data.clear()
    await update.message.reply_text(
        "Let's log your sleep.\n\n"
        "Use /cancel to cancel anytime."
    )
    await update.message.reply_text(
        "When did you go to sleep?",
        reply_markup=make_markup(DATE_KEYBOARD_WITH_NOW)
    )
    return SLEEP_DATE


async def handle_sleep_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sleep date selection."""
    query = update.callback_query
    await query.answer()

    if query.data == "now":
        # Quick option: set sleep time to now and move to wake time
        sleep_datetime = datetime.now()
        context.chat_data['sleep_time'] = sleep_datetime
        await query.edit_message_text(f"Sleep time: {readable_datetime(sleep_datetime)}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="When did you wake up?",
            reply_markup=make_markup(DATE_KEYBOARD_WITH_NOW)
        )
        return WAKE_DATE

    if query.data == "other":
        await query.edit_message_text(
            "Enter the date (DD/MM or DD/MM/YYYY):\n\n"
            "Example: 25/12 or 25/12/2024"
        )
        context.chat_data['custom_date_for'] = 'sleep'
        return CUSTOM_SLEEP_DATE

    context.chat_data['sleep_date'] = parse_date_selection(query.data)

    await query.edit_message_text(
        "What hour did you fall asleep?",
        reply_markup=make_markup(HOUR_KEYBOARD_WITH_NOW)
    )
    return SLEEP_HOUR


async def handle_sleep_hour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sleep hour selection."""
    query = update.callback_query
    await query.answer()

    if query.data == "now":
        # Quick option: set sleep time to now and move to wake time
        sleep_datetime = datetime.now()
        context.chat_data['sleep_time'] = sleep_datetime
        await query.edit_message_text(f"Sleep time: {readable_datetime(sleep_datetime)}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="When did you wake up?",
            reply_markup=make_markup(DATE_KEYBOARD_WITH_NOW)
        )
        return WAKE_DATE

    hour = int(query.data)
    context.chat_data['sleep_hour'] = hour

    minute_keyboard = generate_minute_keyboard(hour)
    await query.edit_message_text(
        "What time exactly?",
        reply_markup=make_markup(minute_keyboard)
    )
    return SLEEP_MINUTE


async def handle_sleep_minute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sleep minute selection."""
    query = update.callback_query
    await query.answer()

    time_str = query.data
    sleep_datetime = combine_date_time(
        context.chat_data['sleep_date'],
        time_str
    )
    context.chat_data['sleep_time'] = sleep_datetime

    # Delete the time selection message
    await query.delete_message()

    # Confirm and ask for wake time
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Sleep time: {readable_datetime(sleep_datetime)}"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="When did you wake up?",
        reply_markup=make_markup(DATE_KEYBOARD_WITH_NOW)
    )
    return WAKE_DATE


async def handle_wake_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wake date selection."""
    query = update.callback_query
    await query.answer()

    if query.data == "now":
        # Quick option: set wake time to now
        wake_datetime = datetime.now()
        sleep_time = context.chat_data['sleep_time']

        # Validate wake time is after sleep time
        if wake_datetime <= sleep_time:
            await query.edit_message_text(
                "Wake time must be after sleep time!\n\n"
                "Please select the wake date:",
                reply_markup=make_markup(DATE_KEYBOARD_WITH_NOW)
            )
            return WAKE_DATE

        context.chat_data['wake_time'] = wake_datetime
        duration = format_duration(sleep_time, wake_datetime)
        await query.edit_message_text(
            f"Wake time: {readable_datetime(wake_datetime)}\n"
            f"Sleep duration: {duration}"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Any notes? (or /skip to skip)"
        )
        return NOTES

    if query.data == "other":
        await query.edit_message_text(
            "Enter the date (DD/MM or DD/MM/YYYY):\n\n"
            "Example: 25/12 or 25/12/2024"
        )
        context.chat_data['custom_date_for'] = 'wake'
        return CUSTOM_WAKE_DATE

    context.chat_data['wake_date'] = parse_date_selection(query.data)

    await query.edit_message_text(
        "What hour did you wake up?",
        reply_markup=make_markup(HOUR_KEYBOARD_WITH_NOW)
    )
    return WAKE_HOUR


async def handle_wake_hour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wake hour selection."""
    query = update.callback_query
    await query.answer()

    if query.data == "now":
        # Quick option: set wake time to now
        wake_datetime = datetime.now()
        sleep_time = context.chat_data['sleep_time']

        # Validate wake time is after sleep time
        if wake_datetime <= sleep_time:
            await query.edit_message_text(
                "Wake time must be after sleep time!\n\n"
                "Please select the wake date:",
                reply_markup=make_markup(DATE_KEYBOARD_WITH_NOW)
            )
            return WAKE_DATE

        context.chat_data['wake_time'] = wake_datetime
        duration = format_duration(sleep_time, wake_datetime)
        await query.edit_message_text(
            f"Wake time: {readable_datetime(wake_datetime)}\n"
            f"Sleep duration: {duration}"
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Any notes? (or /skip to skip)"
        )
        return NOTES

    hour = int(query.data)
    context.chat_data['wake_hour'] = hour

    minute_keyboard = generate_minute_keyboard(hour)
    await query.edit_message_text(
        "What time exactly?",
        reply_markup=make_markup(minute_keyboard)
    )
    return WAKE_MINUTE


async def handle_wake_minute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wake minute selection and validate times."""
    query = update.callback_query
    await query.answer()

    time_str = query.data
    wake_datetime = combine_date_time(
        context.chat_data['wake_date'],
        time_str
    )

    # Validate wake time is after sleep time
    sleep_time = context.chat_data['sleep_time']
    if wake_datetime <= sleep_time:
        await query.edit_message_text(
            "Wake time must be after sleep time!\n\n"
            "Please select the wake date again:",
            reply_markup=make_markup(DATE_KEYBOARD)
        )
        return WAKE_DATE

    context.chat_data['wake_time'] = wake_datetime

    # Delete the time selection message
    await query.delete_message()

    # Confirm and ask for notes
    duration = format_duration(sleep_time, wake_datetime)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Wake time: {readable_datetime(wake_datetime)}\n"
             f"Sleep duration: {duration}"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Any notes? (or /skip to skip)"
    )
    return NOTES


async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle notes input."""
    notes = update.message.text.strip()
    context.chat_data['notes'] = notes
    return await save_sleep_record(update, context)


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip notes."""
    context.chat_data['notes'] = ""
    return await save_sleep_record(update, context)


async def save_sleep_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save sleep record to database."""
    chat_id = update.effective_chat.id
    chat_data = context.chat_data

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        sleep_time = chat_data.get('sleep_time')
        wake_time = chat_data.get('wake_time')
        notes = chat_data.get('notes', '')

        if not sleep_time or not wake_time:
            await update.effective_message.reply_text("Error: Missing time data. Please try /sleep again.")
            clear_chat_data(context)
            return ConversationHandler.END

        record = Wakesleep(
            user_id=user.id,
            sleeptime=sleep_time,
            wakeuptime=wake_time,
            notes=notes,
            created_at=datetime.now()
        )

        try:
            session.add(record)
            session.commit()

            logger.info(f"Sleep record saved: {record}")

            duration = format_duration(sleep_time, wake_time)
            await update.effective_message.reply_text(
                f"Sleep logged!\n\n"
                f"<b>Slept:</b> {readable_datetime(record.sleeptime)}\n"
                f"<b>Woke:</b> {readable_datetime(record.wakeuptime)}\n"
                f"<b>Duration:</b> {duration}\n"
                f"<b>Notes:</b> {record.notes or '-'}",
                parse_mode="HTML"
            )
            await update.effective_message.reply_text(
                "Use /mysleep to view your sleep history."
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving sleep record: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Error saving sleep record. Please try /sleep again."
            )
        finally:
            clear_chat_data(context)

    return ConversationHandler.END


async def my_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's sleep history."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        records = (
            session.query(Wakesleep)
            .filter(Wakesleep.user_id == user.id)
            .order_by(desc(Wakesleep.wakeuptime))
            .limit(5)
            .all()
        )

        if records:
            messages = ["<b>Recent sleep logs:</b>\n"]
            for record in records:
                duration = format_duration(record.sleeptime, record.wakeuptime)
                messages.append(
                    f"{readable_datetime(record.sleeptime)} - "
                    f"{readable_datetime(record.wakeuptime)} "
                    f"({duration})"
                )
            await update.effective_message.reply_text(
                "\n".join(messages),
                parse_mode="HTML"
            )
        else:
            await update.effective_message.reply_text(
                "No sleep records yet. Use /sleep to log your first one!"
            )


async def handle_custom_sleep_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom sleep date input."""
    text = update.message.text.strip()
    parsed_date = parse_custom_date(text)

    if not parsed_date:
        await update.message.reply_text(
            "Invalid date format. Please use DD/MM or DD/MM/YYYY.\n\n"
            "Example: 25/12 or 25/12/2024"
        )
        return CUSTOM_SLEEP_DATE

    context.chat_data['sleep_date'] = parsed_date
    await update.message.reply_text(
        f"Date: {parsed_date.strftime('%d %b %Y')}\n\n"
        "What hour did you fall asleep?",
        reply_markup=make_markup(HOUR_KEYBOARD_WITH_NOW)
    )
    return SLEEP_HOUR


async def handle_custom_wake_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom wake date input."""
    text = update.message.text.strip()
    parsed_date = parse_custom_date(text)

    if not parsed_date:
        await update.message.reply_text(
            "Invalid date format. Please use DD/MM or DD/MM/YYYY.\n\n"
            "Example: 25/12 or 25/12/2024"
        )
        return CUSTOM_WAKE_DATE

    context.chat_data['wake_date'] = parsed_date
    await update.message.reply_text(
        f"Date: {parsed_date.strftime('%d %b %Y')}\n\n"
        "What hour did you wake up?",
        reply_markup=make_markup(HOUR_KEYBOARD_WITH_NOW)
    )
    return WAKE_HOUR


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel sleep logging."""
    logger.info("Sleep logging cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text("Sleep logging cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Sleep logging timed out")
    clear_chat_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"Sleep logging timed out. Please use /sleep to try again."
        )
    return ConversationHandler.END


# Build the conversation handler
wakesleep_handler = ConversationHandler(
    entry_points=[
        CommandHandler('sleep', sleep),
        CommandHandler('wakesleep', sleep),  # Backwards compatibility
    ],
    states={
        SLEEP_DATE: [
            CallbackQueryHandler(handle_sleep_date, pattern=DATE_PATTERN)
        ],
        CUSTOM_SLEEP_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_sleep_date)
        ],
        SLEEP_HOUR: [
            CallbackQueryHandler(handle_sleep_hour, pattern=HOUR_PATTERN)
        ],
        SLEEP_MINUTE: [
            CallbackQueryHandler(handle_sleep_minute, pattern=MINUTE_PATTERN)
        ],
        WAKE_DATE: [
            CallbackQueryHandler(handle_wake_date, pattern=DATE_PATTERN)
        ],
        CUSTOM_WAKE_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_wake_date)
        ],
        WAKE_HOUR: [
            CallbackQueryHandler(handle_wake_hour, pattern=HOUR_PATTERN)
        ],
        WAKE_MINUTE: [
            CallbackQueryHandler(handle_wake_minute, pattern=MINUTE_PATTERN)
        ],
        NOTES: [
            CommandHandler('skip', skip_notes),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notes)
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('cancel_wakesleep', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)

# Export for main.py
mywakesleep = my_sleep
