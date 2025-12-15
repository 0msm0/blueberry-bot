"""
Thoughts/journaling conversation handler.
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
from models import User, Thought
from utils.logger import get_logger
from utils.formatters import readable_datetime, join_items, display_items
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data, append_to_chat_data_list

logger = get_logger(__name__)

# Conversation states
WRITING = 0

# Configuration
TIMEOUT_SECONDS = 300  # 5 minutes for journaling
MAX_LENGTH = 2000


async def thought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for thought/journal logging."""
    chat_id = update.message.chat_id

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

    context.chat_data.clear()
    await update.message.reply_text(
        "Write your thoughts.\n\n"
        "Send multiple messages if needed.\n"
        "Use /done when finished or /cancel to cancel."
    )
    return WRITING


async def handle_thought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle thought input."""
    text = update.message.text.strip()

    if len(text) > MAX_LENGTH:
        await update.message.reply_text(f"Message too long (max {MAX_LENGTH} chars). Please shorten it.")
        return WRITING

    append_to_chat_data_list(context, 'thoughts', text)
    preview = text[:50] + "..." if len(text) > 50 else text
    await update.message.reply_text(f"✓ Saved: \"{preview}\"\n\nContinue writing or /done to finish.")
    return WRITING


async def done_thought(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish adding thoughts."""
    thoughts = context.chat_data.get('thoughts', [])

    if not thoughts:
        await update.message.reply_text("Please write at least one thought.")
        return WRITING

    return await save_thought_record(update, context)


async def save_thought_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save thought record to database."""
    chat_id = update.effective_chat.id
    chat_data = context.chat_data

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        content = join_items(chat_data.get('thoughts', []))

        record = Thought(
            user_id=user.id,
            content=content,
            created_at=datetime.now()
        )

        try:
            session.add(record)
            session.commit()

            logger.info(f"Thought record saved: {record}")

            preview = content[:200] + "..." if len(content) > 200 else content
            await update.effective_message.reply_text(
                f"Thought saved!\n\n"
                f"<b>Time:</b> {readable_datetime(record.created_at)}\n"
                f"<b>Content:</b> {display_items(content)}",
                parse_mode="HTML"
            )
            await update.effective_message.reply_text(
                "Use /mythoughts to view your journal."
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving thought: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Error saving thought. Please try /thought again."
            )
        finally:
            clear_chat_data(context)

    return ConversationHandler.END


async def my_thoughts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's thought history."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        records = (
            session.query(Thought)
            .filter(Thought.user_id == user.id)
            .order_by(desc(Thought.created_at))
            .limit(5)
            .all()
        )

        if records:
            await update.effective_message.reply_text("<b>Recent thoughts:</b>\n", parse_mode="HTML")
            for i, record in enumerate(records, 1):
                content = display_items(record.content)
                preview = content[:150] + "..." if len(content) > 150 else content
                await update.effective_message.reply_text(
                    f"{i}. {readable_datetime(record.created_at)}\n{preview}"
                )
        else:
            await update.effective_message.reply_text(
                "No thoughts recorded yet. Use /thought to start journaling!"
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel thought logging."""
    logger.info("Thought logging cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text("Thought logging cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Thought logging timed out")
    clear_chat_data(context)
    await update.effective_message.reply_text(
        "Thought logging timed out. Please use /thought to try again."
    )
    return ConversationHandler.END


# Build the conversation handler
thoughts_handler = ConversationHandler(
    entry_points=[CommandHandler('thought', thought)],
    states={
        WRITING: [
            CommandHandler('done', done_thought),
            CommandHandler('donethought', done_thought),  # Backwards compatibility
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_thought)
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout)]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('cancelthought', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)

# Export for main.py
mythought = my_thoughts
