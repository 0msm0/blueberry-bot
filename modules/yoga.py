"""
Yoga session tracking conversation handler.

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
from models import User, Yoga
from utils.logger import get_logger
from utils.keyboards import (
    generate_minute_keyboard,
    generate_number_keyboard,
    generate_options_keyboard,
    make_markup,
    DATE_KEYBOARD,
    HOUR_KEYBOARD,
)
from utils.patterns import DATE_PATTERN, HOUR_PATTERN, MINUTE_PATTERN
from utils.formatters import readable_datetime, parse_date_selection, combine_date_time
from modules.getcurrentuser import get_user_with_timezone
from modules.helpers import clear_chat_data

logger = get_logger(__name__)

# Conversation states
DATE, HOUR, MINUTE, YOGA_TYPE, REPS, NOTES = range(6)

# Configuration
TIMEOUT_SECONDS = 600  # 10 minutes

# Yoga types - expanded list
YOGA_TYPES = [
    ("Surya Namaskar", "surya_namaskar"),
    ("Adho Mukha Svanasana", "adho_mukha_svanasana"),
    ("Ardha Chandrasana", "ardha_chandrasana"),
    ("Balasana", "balasana"),
    ("Bhujangasana", "bhujangasana"),
    ("Chakrasana", "chakrasana"),
    ("Garudasana", "garudasana"),
    ("Gomukhasana", "gomukhasana"),
    ("Shavasana", "shavasana"),
    ("Shirshasana", "shirshasana"),
    ("Sukhasana", "sukhasana"),
    ("Vajrasana", "vajrasana"),
    ("Other", "other"),
]

YOGA_TYPE_KEYBOARD = generate_options_keyboard(YOGA_TYPES, columns=3)
YOGA_TYPE_PATTERN = "^" + "|".join([opt[1] for opt in YOGA_TYPES]) + "$"


async def yoga(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for yoga logging."""
    chat_id = update.message.chat_id

    with Session() as session:
        user = await get_user_with_timezone(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

    context.chat_data.clear()
    await update.message.reply_text(
        "Let's log your yoga session.\n\n"
        "Use /cancel to cancel anytime."
    )
    await update.message.reply_text(
        "When did you do yoga?",
        reply_markup=make_markup(DATE_KEYBOARD)
    )
    return DATE


async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "other":
        await query.edit_message_text("Custom date coming soon! Use /yoga again.")
        return ConversationHandler.END

    context.chat_data['yoga_date'] = parse_date_selection(query.data)
    await query.edit_message_text("What hour?", reply_markup=make_markup(HOUR_KEYBOARD))
    return HOUR


async def handle_hour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    hour = int(query.data)
    context.chat_data['yoga_hour'] = hour
    await query.edit_message_text(
        "What time exactly?",
        reply_markup=make_markup(generate_minute_keyboard(hour))
    )
    return MINUTE


async def handle_minute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    yoga_datetime = combine_date_time(context.chat_data['yoga_date'], query.data)
    context.chat_data['yoga_datetime'] = yoga_datetime
    await query.edit_message_text(
        f"Time: {readable_datetime(yoga_datetime)}\n\nWhat type of yoga?",
        reply_markup=make_markup(YOGA_TYPE_KEYBOARD)
    )
    return YOGA_TYPE


async def handle_yoga_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.chat_data['yoga_type'] = query.data
    reps_keyboard = generate_number_keyboard(1, 20, columns=5)
    await query.edit_message_text(
        f"Type: {query.data.replace('_', ' ').title()}\n\nHow many repetitions/rounds?",
        reply_markup=make_markup(reps_keyboard)
    )
    return REPS


async def handle_reps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.chat_data['yoga_reps'] = int(query.data)
    await query.edit_message_text("Any notes? (or /skip)")
    return NOTES


async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['yoga_notes'] = update.message.text.strip()
    return await save_yoga_record(update, context)


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.chat_data['yoga_notes'] = ""
    return await save_yoga_record(update, context)


async def save_yoga_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    chat_data = context.chat_data

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        record = Yoga(
            user_id=user.id,
            yoga_datetime=chat_data.get('yoga_datetime'),
            yoga_type=chat_data.get('yoga_type'),
            repetition=chat_data.get('yoga_reps'),
            yoga_notes=chat_data.get('yoga_notes', ''),
            created_at=datetime.now()
        )

        try:
            session.add(record)
            session.commit()
            logger.info(f"Yoga record saved: {record}")
            await update.effective_message.reply_text(
                f"Yoga session logged!\n\n"
                f"<b>Time:</b> {readable_datetime(record.yoga_datetime)}\n"
                f"<b>Type:</b> {record.yoga_type.replace('_', ' ').title()}\n"
                f"<b>Reps:</b> {record.repetition}\n"
                f"<b>Notes:</b> {record.yoga_notes or '-'}",
                parse_mode="HTML"
            )
            await update.effective_message.reply_text("Use /myyoga to view your yoga history.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving yoga: {e}", exc_info=True)
            await update.effective_message.reply_text("Error saving. Try /yoga again.")
        finally:
            clear_chat_data(context)

    return ConversationHandler.END


async def my_yoga(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        records = (
            session.query(Yoga)
            .filter(Yoga.user_id == user.id)
            .order_by(desc(Yoga.yoga_datetime))
            .limit(5)
            .all()
        )

        if records:
            for r in records:
                text = (
                    f"<b>{r.yoga_type.replace('_', ' ').title()}</b> - {r.repetition} reps\n"
                    f"{readable_datetime(r.yoga_datetime)}"
                )
                if r.yoga_notes:
                    text += f"\nNote: {r.yoga_notes}"
                await update.effective_message.reply_text(text, parse_mode="HTML")
        else:
            await update.effective_message.reply_text("No yoga records. Use /yoga to log!")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Yoga logging cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text("Yoga logging cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Yoga logging timed out")
    clear_chat_data(context)
    await update.effective_message.reply_text("Yoga logging timed out.")
    return ConversationHandler.END


yoga_handler = ConversationHandler(
    entry_points=[CommandHandler('yoga', yoga)],
    states={
        DATE: [CallbackQueryHandler(handle_date, pattern=DATE_PATTERN)],
        HOUR: [CallbackQueryHandler(handle_hour, pattern=HOUR_PATTERN)],
        MINUTE: [CallbackQueryHandler(handle_minute, pattern=MINUTE_PATTERN)],
        YOGA_TYPE: [CallbackQueryHandler(handle_yoga_type, pattern=YOGA_TYPE_PATTERN)],
        REPS: [CallbackQueryHandler(handle_reps, pattern="^[0-9]+$")],
        NOTES: [
            CommandHandler('skip', skip_notes),
            CommandHandler('skip_notes', skip_notes),  # Backwards compatibility
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notes)
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout)]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('cancelyoga', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)

myyoga = my_yoga
