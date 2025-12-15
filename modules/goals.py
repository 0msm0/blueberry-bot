"""
Goals/North Star feature - Simple text-based wellness goals.

Requires python-telegram-bot v21+
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

from dbhelper import Session
from models import User, Goal
from utils.logger import get_logger
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data

logger = get_logger(__name__)

# Conversation states
VIEW_GOALS, ENTER_GOAL = range(2)

TIMEOUT_SECONDS = 300


def format_goals_message(goals_dict: dict) -> str:
    """Format all goals for display."""
    lines = ["<b>Your Wellness Goals</b>\n"]
    lines.append("Your north star for each area:\n")

    for area, display_name in Goal.AREAS:
        goal = goals_dict.get(area)
        if goal:
            lines.append(f"<b>{display_name}:</b> {goal.goal_text}")
        else:
            lines.append(f"<b>{display_name}:</b> <i>(not set)</i>")

    lines.append("\nSelect an area to set or update its goal:")
    return "\n".join(lines)


def get_goals_keyboard():
    """Generate goals menu keyboard."""
    keyboard = []
    for area, display_name in Goal.AREAS:
        keyboard.append([InlineKeyboardButton(
            f"Set {display_name} Goal",
            callback_data=f"goal_{area}"
        )])
    keyboard.append([InlineKeyboardButton("Done", callback_data="done")])
    return InlineKeyboardMarkup(keyboard)


async def goals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /goals command."""
    chat_id = update.message.chat_id
    logger.info(f"[User:{chat_id}] Opening goals menu")

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

        # Get all goals for user
        all_goals = Goal.get_all_for_user(session, user.id)
        goals_dict = {g.area: g for g in all_goals}

        message = format_goals_message(goals_dict)
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=get_goals_keyboard()
        )

    context.chat_data.clear()
    return VIEW_GOALS


async def handle_goal_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goal area selection."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id

    if query.data == "done":
        await query.edit_message_text("Goals saved!")
        clear_chat_data(context)
        return ConversationHandler.END

    if query.data.startswith("goal_"):
        area = query.data[5:]  # Remove "goal_" prefix
        context.chat_data['editing_area'] = area

        # Find display name
        display_name = next((d for a, d in Goal.AREAS if a == area), area)

        # Get current goal if exists
        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                current_goal = Goal.get_by_user_and_area(session, user.id, area)
                if current_goal:
                    current_text = f"\n\n<b>Current goal:</b> {current_goal.goal_text}"
                else:
                    current_text = ""

        examples = {
            'sleep': '"Sleep by 10 PM daily"\n"Get 7-8 hours of sleep"',
            'food': '"No junk food on weekdays"\n"Eat more vegetables"',
            'gym': '"4 gym sessions per week"\n"Increase bench press to 80kg"',
            'yoga': '"Daily morning yoga"\n"Hold each pose for 1 minute"',
            'pranayam': '"10 minutes pranayam daily"\n"Practice before breakfast"',
        }

        example_text = examples.get(area, '"Set a meaningful goal"')

        await query.edit_message_text(
            f"<b>Set {display_name} Goal</b>{current_text}\n\n"
            f"Enter your goal for {display_name.lower()}.\n\n"
            f"<b>Examples:</b>\n{example_text}\n\n"
            f"Send your goal or /cancel to go back.",
            parse_mode="HTML"
        )
        return ENTER_GOAL

    return VIEW_GOALS


async def handle_goal_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goal text input."""
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    area = context.chat_data.get('editing_area')

    if not area:
        await update.message.reply_text("Error: No area selected. Use /goals to start again.")
        clear_chat_data(context)
        return ConversationHandler.END

    if not text:
        await update.message.reply_text("Please enter a goal. It cannot be empty.")
        return ENTER_GOAL

    if len(text) > 500:
        await update.message.reply_text("Goal is too long (max 500 characters). Please shorten it.")
        return ENTER_GOAL

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        try:
            # Set or update the goal
            Goal.set_goal(session, user.id, area, text)
            session.commit()

            # Get all goals to show updated menu
            all_goals = Goal.get_all_for_user(session, user.id)
            goals_dict = {g.area: g for g in all_goals}

            display_name = next((d for a, d in Goal.AREAS if a == area), area)
            logger.info(f"[User:{chat_id}] Set {area} goal: {text[:50]}...")

            await update.message.reply_text(f"{display_name} goal saved!")

            message = format_goals_message(goals_dict)
            await update.message.reply_text(
                message,
                parse_mode="HTML",
                reply_markup=get_goals_keyboard()
            )
        except Exception as e:
            session.rollback()
            logger.error(f"[User:{chat_id}] Error saving goal: {e}", exc_info=True)
            await update.message.reply_text("Error saving goal. Please try again.")

    context.chat_data.pop('editing_area', None)
    return VIEW_GOALS


async def cancel_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel goals editing."""
    chat_id = update.effective_chat.id
    logger.info(f"[User:{chat_id}] Cancelled goals")
    clear_chat_data(context)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Goals cancelled.")
    else:
        await update.effective_message.reply_text("Goals cancelled.")

    return ConversationHandler.END


async def timeout_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goals timeout."""
    logger.info("Goals timed out")
    clear_chat_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Goals timed out. Use /goals to try again."
        )
    return ConversationHandler.END


async def mygoals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick view of all goals (no conversation)."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        all_goals = Goal.get_all_for_user(session, user.id)
        goals_dict = {g.area: g for g in all_goals}

        lines = ["<b>Your Wellness Goals</b>\n"]

        has_goals = False
        for area, display_name in Goal.AREAS:
            goal = goals_dict.get(area)
            if goal:
                has_goals = True
                lines.append(f"<b>{display_name}:</b> {goal.goal_text}")

        if not has_goals:
            lines.append("No goals set yet.")
            lines.append("\nUse /goals to set your wellness goals!")
        else:
            lines.append("\nUse /goals to update your goals.")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


# Conversation handler
goals_handler = ConversationHandler(
    entry_points=[CommandHandler('goals', goals_command)],
    states={
        VIEW_GOALS: [
            CallbackQueryHandler(handle_goal_selection),
        ],
        ENTER_GOAL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_goal_input),
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout_goals),
            CallbackQueryHandler(timeout_goals),
        ],
    },
    fallbacks=[
        CommandHandler('cancel', cancel_goals),
    ],
    conversation_timeout=TIMEOUT_SECONDS,
)
