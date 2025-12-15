"""
Completed tasks tracking conversation handler.
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
from sqlalchemy import desc

from dbhelper import Session
from models import User, Task
from utils.logger import get_logger
from utils.formatters import readable_datetime, join_items, display_items
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data, append_to_chat_data_list

logger = get_logger(__name__)

# Conversation states
WRITING = 0

# Configuration
TIMEOUT_SECONDS = 300
MAX_LENGTH = 1000


async def task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for task logging."""
    chat_id = update.message.chat_id

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

    context.chat_data.clear()
    await update.message.reply_text(
        "Log your completed tasks.\n\n"
        "Send each task as a separate message.\n"
        "Use /done when finished or /cancel to cancel."
    )
    return WRITING


async def handle_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle task input."""
    text = update.message.text.strip()

    if len(text) > MAX_LENGTH:
        await update.message.reply_text(f"Task too long (max {MAX_LENGTH} chars). Please shorten it.")
        return WRITING

    append_to_chat_data_list(context, 'tasks', text)
    count = len(context.chat_data.get('tasks', []))
    await update.message.reply_text(f"✓ Task {count} added: {text}\n\nAdd more or /done to finish.")
    return WRITING


async def done_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish adding tasks."""
    tasks = context.chat_data.get('tasks', [])

    if not tasks:
        await update.message.reply_text("Please add at least one task.")
        return WRITING

    return await save_task_record(update, context)


async def save_task_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save task record to database."""
    chat_id = update.effective_chat.id
    chat_data = context.chat_data

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        content = join_items(chat_data.get('tasks', []))

        record = Task(
            user_id=user.id,
            content=content,
            created_at=datetime.now()
        )

        try:
            session.add(record)
            session.commit()

            logger.info(f"Task record saved: {record}")

            tasks_list = chat_data.get('tasks', [])
            await update.effective_message.reply_text(
                f"Tasks logged!\n\n"
                f"<b>Time:</b> {readable_datetime(record.created_at)}\n"
                f"<b>Tasks:</b>\n" + "\n".join(f"- {t}" for t in tasks_list),
                parse_mode="HTML"
            )
            await update.effective_message.reply_text(
                "Use /mytasks to view your completed tasks."
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving task: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Error saving tasks. Please try /task again."
            )
        finally:
            clear_chat_data(context)

    return ConversationHandler.END


async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's task history."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        records = (
            session.query(Task)
            .filter(Task.user_id == user.id)
            .order_by(desc(Task.created_at))
            .limit(5)
            .all()
        )

        if records:
            await update.effective_message.reply_text("<b>Recent completed tasks:</b>\n", parse_mode="HTML")
            for record in records:
                tasks = display_items(record.content)
                await update.effective_message.reply_text(
                    f"{readable_datetime(record.created_at)}\n{tasks}"
                )
        else:
            await update.effective_message.reply_text(
                "No tasks recorded yet. Use /task to log completed tasks!"
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel task logging."""
    logger.info("Task logging cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text("Task logging cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Task logging timed out")
    clear_chat_data(context)
    await update.effective_message.reply_text(
        "Task logging timed out. Please use /task to try again."
    )
    return ConversationHandler.END


# Build the conversation handler
taskcompleted_handler = ConversationHandler(
    entry_points=[
        CommandHandler('task', task),
        CommandHandler('taskcompleted', task),  # Backwards compatibility
    ],
    states={
        WRITING: [
            CommandHandler('done', done_tasks),
            CommandHandler('donetask', done_tasks),  # Backwards compatibility
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task)
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout)]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('canceltask', cancel),
        CommandHandler('canceltaskcompleted', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)

# Export for main.py
mytaskcompleted = my_tasks
