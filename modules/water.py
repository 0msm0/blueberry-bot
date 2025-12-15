"""
Water intake logging conversation handler.

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
from sqlalchemy import desc, func

from dbhelper import Session
from models import User, Water
from utils.logger import get_logger
from utils.keyboards import (
    generate_minute_keyboard,
    generate_options_keyboard,
    make_markup,
    DATE_KEYBOARD,
    HOUR_KEYBOARD,
)
from utils.patterns import DATE_PATTERN, HOUR_PATTERN, MINUTE_PATTERN
from utils.formatters import (
    readable_datetime,
    parse_date_selection,
    combine_date_time,
)
from modules.getcurrentuser import get_user_with_timezone
from modules.helpers import clear_chat_data

logger = get_logger(__name__)

# Conversation states
DATE, HOUR, MINUTE, AMOUNT, NOTES = range(5)

# Configuration
TIMEOUT_SECONDS = 600  # 10 minutes

# Water amount options (in ml)
WATER_AMOUNTS = [
    ("1 Glass (250ml)", "250"),
    ("2 Glasses (500ml)", "500"),
    ("3 Glasses (750ml)", "750"),
    ("1 Litre", "1000"),
    ("1.5 Litres", "1500"),
    ("2 Litres", "2000"),
]
WATER_AMOUNT_KEYBOARD = generate_options_keyboard(WATER_AMOUNTS, columns=2)
WATER_AMOUNT_PATTERN = "^(250|500|750|1000|1500|2000)$"


async def water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for water logging."""
    chat_id = update.message.chat_id
    logger.info(f"[User:{chat_id}] Starting water logging")

    with Session() as session:
        user = await get_user_with_timezone(chat_id, update, context, session)
        if not user:
            logger.warning(f"[User:{chat_id}] Water logging aborted - user not found or no timezone")
            return ConversationHandler.END

    context.chat_data.clear()
    await update.message.reply_text(
        "Let's log your water intake.\n\n"
        "Use /cancel to cancel anytime."
    )
    await update.message.reply_text(
        "When did you drink water?",
        reply_markup=make_markup(DATE_KEYBOARD)
    )
    return DATE


async def handle_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle date selection."""
    query = update.callback_query
    await query.answer()

    if query.data == "other":
        await query.edit_message_text(
            "Custom date selection coming soon!\n"
            "Please use /water again and select a recent date."
        )
        return ConversationHandler.END

    context.chat_data['water_date'] = parse_date_selection(query.data)

    await query.edit_message_text(
        "What hour?",
        reply_markup=make_markup(HOUR_KEYBOARD)
    )
    return HOUR


async def handle_hour(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle hour selection."""
    query = update.callback_query
    await query.answer()

    hour = int(query.data)
    context.chat_data['water_hour'] = hour

    minute_keyboard = generate_minute_keyboard(hour)
    await query.edit_message_text(
        "What time exactly?",
        reply_markup=make_markup(minute_keyboard)
    )
    return MINUTE


async def handle_minute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle minute selection."""
    query = update.callback_query
    await query.answer()

    time_str = query.data
    water_datetime = combine_date_time(
        context.chat_data['water_date'],
        time_str
    )
    context.chat_data['water_time'] = water_datetime

    await query.edit_message_text(
        f"Time: {readable_datetime(water_datetime)}\n\n"
        "How much water did you drink?",
        reply_markup=make_markup(WATER_AMOUNT_KEYBOARD)
    )
    return AMOUNT


async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle amount selection."""
    query = update.callback_query
    await query.answer()

    amount_ml = int(query.data)
    context.chat_data['water_amount'] = amount_ml

    await query.edit_message_text(
        f"Amount: {amount_ml}ml\n\n"
        "Any notes? (or /skip)"
    )
    return NOTES


async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle notes input."""
    chat_id = update.effective_chat.id
    notes = update.message.text.strip()
    context.chat_data['water_notes'] = notes
    logger.debug(f"[User:{chat_id}] Water notes added: {notes[:50]}...")

    return await save_water_record(update, context)


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip notes."""
    chat_id = update.effective_chat.id
    logger.debug(f"[User:{chat_id}] Skipping water notes")
    context.chat_data['water_notes'] = ""

    return await save_water_record(update, context)


async def save_water_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save water record to database."""
    chat_id = update.effective_chat.id
    chat_data = context.chat_data

    logger.debug(f"[User:{chat_id}] Saving water record. chat_data keys: {list(chat_data.keys())}")

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            logger.error(f"[User:{chat_id}] User not found when saving water record")
            await update.effective_message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        water_time = chat_data.get('water_time')
        amount_ml = chat_data.get('water_amount')
        water_notes = chat_data.get('water_notes', '')

        logger.debug(f"[User:{chat_id}] Water data - time: {water_time}, amount: {amount_ml}ml")

        record = Water(
            user_id=user.id,
            water_time=water_time,
            amount_ml=amount_ml,
            water_notes=water_notes,
            created_at=datetime.now()
        )

        try:
            session.add(record)
            session.commit()

            logger.info(f"Water record saved: {record}")

            glasses = amount_ml / 250
            await update.effective_message.reply_text(
                f"Water intake logged!\n\n"
                f"<b>Time:</b> {readable_datetime(record.water_time)}\n"
                f"<b>Amount:</b> {record.amount_ml}ml ({glasses:.1f} glasses)\n"
                f"<b>Notes:</b> {record.water_notes or '-'}",
                parse_mode="HTML"
            )
            await update.effective_message.reply_text(
                "Use /mywater to view your water intake history."
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving water record: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Error saving water record. Please try /water again."
            )
        finally:
            clear_chat_data(context)

    return ConversationHandler.END


async def my_water(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's water intake history."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        # Get today's total
        today = datetime.now().date()
        today_total = (
            session.query(func.sum(Water.amount_ml))
            .filter(Water.user_id == user.id)
            .filter(func.date(Water.water_time) == today)
            .scalar()
        ) or 0

        # Get recent records
        records = (
            session.query(Water)
            .filter(Water.user_id == user.id)
            .order_by(desc(Water.water_time))
            .limit(10)
            .all()
        )

        if records:
            today_glasses = today_total / 250
            header = (
                f"<b>Today's Total:</b> {today_total}ml ({today_glasses:.1f} glasses)\n\n"
                f"<b>Recent Water Intake:</b>"
            )
            await update.effective_message.reply_text(header, parse_mode="HTML")

            for i, record in enumerate(records):
                glasses = record.amount_ml / 250
                text = (
                    f"{i+1}. {readable_datetime(record.water_time)}\n"
                    f"   {record.amount_ml}ml ({glasses:.1f} glasses)"
                )
                if record.water_notes:
                    text += f"\n   Notes: {record.water_notes}"
                await update.effective_message.reply_text(text)
        else:
            await update.effective_message.reply_text(
                "No water records yet. Use /water to log your first intake!"
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel water logging."""
    logger.info("Water logging cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text("Water logging cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Water logging timed out")
    clear_chat_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Water logging timed out. Please use /water to try again."
        )
    return ConversationHandler.END


# Build the conversation handler
water_handler = ConversationHandler(
    entry_points=[CommandHandler('water', water)],
    states={
        DATE: [CallbackQueryHandler(handle_date, pattern=DATE_PATTERN)],
        HOUR: [CallbackQueryHandler(handle_hour, pattern=HOUR_PATTERN)],
        MINUTE: [CallbackQueryHandler(handle_minute, pattern=MINUTE_PATTERN)],
        AMOUNT: [CallbackQueryHandler(handle_amount, pattern=WATER_AMOUNT_PATTERN)],
        NOTES: [
            CommandHandler('skip', skip_notes),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notes)
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout)]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
    ],
    conversation_timeout=TIMEOUT_SECONDS
)
