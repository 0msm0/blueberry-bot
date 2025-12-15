"""
Gym workout tracking conversation handler.
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
from models import User, Gym
from utils.logger import get_logger
from utils.keyboards import (
    generate_minute_keyboard,
    generate_number_keyboard,
    make_markup,
    DATE_KEYBOARD,
    HOUR_KEYBOARD,
    GYM_TYPE_KEYBOARD,
)
from utils.patterns import (
    DATE_PATTERN,
    HOUR_PATTERN,
    MINUTE_PATTERN,
    GYM_TYPE_PATTERN,
    SETS_PATTERN,
    REPS_PATTERN,
    WEIGHT_PATTERN,
)
from utils.formatters import (
    readable_datetime,
    parse_date_selection,
    combine_date_time,
)
from modules.getcurrentuser import get_user_with_timezone
from modules.helpers import clear_chat_data, append_to_chat_data_list

logger = get_logger(__name__)

# Conversation states
DATE, HOUR, MINUTE, EXERCISE_TYPE, SETS, REPS, WEIGHT, NOTES = range(8)

# Configuration
TIMEOUT_SECONDS = 180


async def gym(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for gym logging."""
    chat_id = update.message.chat_id

    with Session() as session:
        user = await get_user_with_timezone(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

    context.chat_data.clear()
    await update.message.reply_text(
        "Let's log your workout.\n\n"
        "Use /cancel to cancel anytime."
    )
    await update.message.reply_text(
        "When did you work out?",
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
            "Please use /gym again and select a recent date."
        )
        return ConversationHandler.END

    context.chat_data['gym_date'] = parse_date_selection(query.data)

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
    context.chat_data['gym_hour'] = hour

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
    gym_datetime = combine_date_time(
        context.chat_data['gym_date'],
        time_str
    )
    context.chat_data['gym_datetime'] = gym_datetime

    await query.edit_message_text(
        f"Time: {readable_datetime(gym_datetime)}\n\n"
        "What exercise did you do?",
        reply_markup=make_markup(GYM_TYPE_KEYBOARD)
    )
    return EXERCISE_TYPE


async def handle_exercise_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle exercise type selection."""
    query = update.callback_query
    await query.answer()

    context.chat_data['gym_type'] = query.data

    sets_keyboard = generate_number_keyboard(1, 10, columns=5)
    await query.edit_message_text(
        f"Exercise: {query.data.replace('_', ' ').title()}\n\n"
        "How many sets?",
        reply_markup=make_markup(sets_keyboard)
    )
    return SETS


async def handle_sets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sets selection."""
    query = update.callback_query
    await query.answer()

    total_sets = int(query.data)
    context.chat_data['total_sets'] = total_sets
    context.chat_data['current_set'] = 1
    context.chat_data['reps'] = []
    context.chat_data['weights'] = []

    reps_keyboard = generate_number_keyboard(1, 20, columns=5)
    await query.edit_message_text(
        f"Set 1 of {total_sets}\n\n"
        "How many reps?",
        reply_markup=make_markup(reps_keyboard)
    )
    return REPS


async def handle_reps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reps selection."""
    query = update.callback_query
    await query.answer()

    append_to_chat_data_list(context, 'reps', query.data)

    weight_keyboard = generate_number_keyboard(1, 50, columns=5, suffix=" kg")
    await query.edit_message_text(
        f"Set {context.chat_data['current_set']} - {query.data} reps\n\n"
        "What weight (kg)?",
        reply_markup=make_markup(weight_keyboard)
    )
    return WEIGHT


async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle weight selection."""
    query = update.callback_query
    await query.answer()

    append_to_chat_data_list(context, 'weights', query.data)

    current_set = context.chat_data['current_set']
    total_sets = context.chat_data['total_sets']

    if current_set < total_sets:
        # More sets to go
        context.chat_data['current_set'] = current_set + 1

        reps_keyboard = generate_number_keyboard(1, 20, columns=5)
        await query.edit_message_text(
            f"Set {current_set + 1} of {total_sets}\n\n"
            "How many reps?",
            reply_markup=make_markup(reps_keyboard)
        )
        return REPS
    else:
        # All sets done
        await query.edit_message_text(
            "Great workout!\n\n"
            "Any notes? (or /skip)"
        )
        return NOTES


async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle notes input."""
    context.chat_data['gym_notes'] = update.message.text.strip()
    return await save_gym_record(update, context)


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip notes."""
    context.chat_data['gym_notes'] = ""
    return await save_gym_record(update, context)


async def save_gym_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save gym record to database."""
    chat_id = update.effective_chat.id
    chat_data = context.chat_data

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        record = Gym(
            user_id=user.id,
            gym_datetime=chat_data.get('gym_datetime'),
            gym_type=chat_data.get('gym_type'),
            total_set=chat_data.get('total_sets'),
            repetition=", ".join(chat_data.get('reps', [])),
            weight=", ".join(chat_data.get('weights', [])),
            gym_notes=chat_data.get('gym_notes', ''),
            created_at=datetime.now()
        )

        try:
            session.add(record)
            session.commit()

            logger.info(f"Gym record saved: {record}")

            await update.effective_message.reply_text(
                f"Workout logged!\n\n"
                f"<b>Time:</b> {readable_datetime(record.gym_datetime)}\n"
                f"<b>Exercise:</b> {record.gym_type.replace('_', ' ').title()}\n"
                f"<b>Sets:</b> {record.total_set}\n"
                f"<b>Details:</b>\n{record.get_sets_formatted()}\n"
                f"<b>Notes:</b> {record.gym_notes or '-'}",
                parse_mode="HTML"
            )
            await update.effective_message.reply_text(
                "Use /mygym to view your workout history."
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving gym record: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Error saving workout. Please try /gym again."
            )
        finally:
            clear_chat_data(context)

    return ConversationHandler.END


async def my_gym(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's gym history."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        records = (
            session.query(Gym)
            .filter(Gym.user_id == user.id)
            .order_by(desc(Gym.gym_datetime))
            .limit(5)
            .all()
        )

        if records:
            for record in records:
                text = (
                    f"<b>{record.gym_type.replace('_', ' ').title()}</b> - "
                    f"{record.total_set} sets\n"
                    f"{record.get_sets_formatted()}\n"
                    f"{readable_datetime(record.gym_datetime)}"
                )
                if record.gym_notes:
                    text += f"\nNote: {record.gym_notes}"
                await update.effective_message.reply_text(text, parse_mode="HTML")
        else:
            await update.effective_message.reply_text(
                "No workout records yet. Use /gym to log your first one!"
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel gym logging."""
    logger.info("Gym logging cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text("Workout logging cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Gym logging timed out")
    clear_chat_data(context)
    await update.effective_message.reply_text(
        "Workout logging timed out. Please use /gym to try again."
    )
    return ConversationHandler.END


# Build the conversation handler
gym_handler = ConversationHandler(
    entry_points=[CommandHandler('gym', gym)],
    states={
        DATE: [CallbackQueryHandler(handle_date, pattern=DATE_PATTERN)],
        HOUR: [CallbackQueryHandler(handle_hour, pattern=HOUR_PATTERN)],
        MINUTE: [CallbackQueryHandler(handle_minute, pattern=MINUTE_PATTERN)],
        EXERCISE_TYPE: [CallbackQueryHandler(handle_exercise_type, pattern=GYM_TYPE_PATTERN)],
        SETS: [CallbackQueryHandler(handle_sets, pattern=SETS_PATTERN)],
        REPS: [CallbackQueryHandler(handle_reps, pattern=REPS_PATTERN)],
        WEIGHT: [CallbackQueryHandler(handle_weight, pattern=WEIGHT_PATTERN)],
        NOTES: [
            CommandHandler('skip', skip_notes),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notes)
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout)]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('cancelgym', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)

# Export for main.py
mygym = my_gym
