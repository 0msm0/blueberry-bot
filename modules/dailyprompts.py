"""
Daily prompts conversation handlers (gratitude, themeoftheday, selflove, affirmation).

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
from models import User, Gratitude, ThemeOfTheDay, SelfLove, Affirmation
from core.scheduler import (
    get_user_local_date,
    schedule_theme_reminders,
)
from utils.logger import get_logger
from utils.formatters import join_items, display_items, readable_date
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data, append_to_chat_data_list

logger = get_logger(__name__)

# Conversation states
COLLECTING = 0

# Timeout
TIMEOUT_SECONDS = 300

# Prompt type to model mapping
PROMPT_MODELS = {
    'gratitude': Gratitude,
    'themeoftheday': ThemeOfTheDay,
    'selflove': SelfLove,
    'affirmation': Affirmation,
}

# Prompt configuration
PROMPT_CONFIG = {
    'gratitude': {
        'command': 'gratitude',
        'question': (
            "What are the top 3 things you are grateful for today?\n\n"
            "Send each item as a separate message.\n"
            "Use /done when finished (minimum 3 items)."
        ),
        'min_items': 3,
        'max_items': 5,
        'item_name': 'gratitude',
        'success_message': "Your gratitude list has been saved!",
        'has_reminders': False,
    },
    'themeoftheday': {
        'command': 'themeoftheday',
        'question': (
            "What is your theme or intention for today?\n\n"
            "This could be a focus area, goal, or mindset.\n"
            "Send your theme in one message."
        ),
        'min_items': 1,
        'max_items': 1,
        'item_name': 'theme',
        'success_message': "Your theme for today has been set!",
        'has_reminders': True,
    },
    'selflove': {
        'command': 'selflove',
        'question': (
            "Write 3 things you love about yourself.\n\n"
            "Take a moment to appreciate who you are.\n"
            "Send each item as a separate message.\n"
            "Use /done when finished (minimum 3 items)."
        ),
        'min_items': 3,
        'max_items': 5,
        'item_name': 'self-love item',
        'success_message': "Your self-love list has been saved!",
        'has_reminders': False,
    },
    'affirmation': {
        'command': 'affirmation',
        'question': (
            "What positive affirmations do you want to set for today?\n\n"
            "Send each affirmation as a separate message.\n"
            "Use /done when finished (minimum 1 affirmation)."
        ),
        'min_items': 1,
        'max_items': 5,
        'item_name': 'affirmation',
        'success_message': "Your affirmations have been saved!",
        'has_reminders': False,
    },
}


def create_prompt_handlers(prompt_type: str):
    """
    Factory function to create conversation handler for a prompt type.
    Returns (conversation_handler, skip_handler_function).
    """
    config = PROMPT_CONFIG[prompt_type]
    Model = PROMPT_MODELS[prompt_type]

    async def start_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Entry point for prompt command."""
        chat_id = update.message.chat_id
        logger.info(f"[User:{chat_id}] Starting {prompt_type} prompt")

        with Session() as session:
            user = await get_current_user(chat_id, update, context, session)
            if not user:
                return ConversationHandler.END

            # Get user's local date
            today = get_user_local_date(user)

            # Check if already answered today
            existing = Model.get_for_date(session, user.id, today)
            if existing:
                await update.message.reply_text(
                    f"You've already answered this today!\n\n"
                    f"<b>Your {config['item_name']}:</b>\n"
                    f"{display_items(existing.content, separator=chr(10))}",
                    parse_mode="HTML"
                )
                return ConversationHandler.END

        context.chat_data.clear()
        context.chat_data['prompt_type'] = prompt_type
        context.chat_data['prompt_date'] = today

        await update.message.reply_text(config['question'])
        return COLLECTING

    async def handle_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle item input."""
        text = update.message.text.strip()

        if not text:
            await update.message.reply_text("Please enter something.")
            return COLLECTING

        # For single-item prompts (theme), save immediately
        if config['max_items'] == 1:
            context.chat_data['items'] = [text]
            return await save_prompt(update, context)

        # Append to list
        append_to_chat_data_list(context, 'items', text)
        count = len(context.chat_data.get('items', []))

        # Check if max reached
        if count >= config['max_items']:
            return await save_prompt(update, context)

        # Provide feedback
        remaining = config['min_items'] - count
        if remaining > 0:
            await update.message.reply_text(
                f"Added! {remaining} more {config['item_name']}(s) needed.\n"
                f"Send another or /done when finished."
            )
        else:
            await update.message.reply_text(
                f"Added! ({count}/{config['max_items']})\n"
                f"Send more or /done to finish."
            )

        return COLLECTING

    async def done_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Finish collecting items."""
        items = context.chat_data.get('items', [])

        if len(items) < config['min_items']:
            await update.message.reply_text(
                f"Please add at least {config['min_items']} {config['item_name']}(s).\n"
                f"You have {len(items)} so far."
            )
            return COLLECTING

        return await save_prompt(update, context)

    async def save_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Save prompt response to database."""
        chat_id = update.effective_chat.id
        items = context.chat_data.get('items', [])
        prompt_date = context.chat_data.get('prompt_date')

        logger.debug(f"[User:{chat_id}] Saving {prompt_type} prompt: {items}")

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if not user:
                await update.effective_message.reply_text("Error: User not found.")
                clear_chat_data(context)
                return ConversationHandler.END

            content = join_items(items)

            # Create record using the appropriate model
            record = Model(
                user_id=user.id,
                prompt_date=prompt_date,
                content=content,
                created_at=datetime.now()
            )

            try:
                session.add(record)
                session.commit()

                logger.info(f"[User:{chat_id}] {prompt_type} prompt saved")

                # Show success message
                await update.effective_message.reply_text(
                    f"{config['success_message']}\n\n"
                    f"<b>{readable_date(prompt_date)}:</b>\n"
                    f"{display_items(content, separator=chr(10))}",
                    parse_mode="HTML"
                )

                # Schedule theme reminders if applicable
                if config.get('has_reminders') and context.job_queue:
                    job_ids = schedule_theme_reminders(
                        context.job_queue,
                        user,
                        content,
                        session
                    )
                    if job_ids:
                        await update.effective_message.reply_text(
                            f"I'll remind you about your theme {len(job_ids)} time(s) today!"
                        )

            except Exception as e:
                session.rollback()
                logger.error(f"Error saving {prompt_type}: {e}", exc_info=True)
                await update.effective_message.reply_text(
                    f"Error saving. Please try /{config['command']} again."
                )
            finally:
                clear_chat_data(context)

        return ConversationHandler.END

    async def skip_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Skip the prompt for today."""
        chat_id = update.effective_chat.id
        logger.info(f"[User:{chat_id}] Skipped {prompt_type} prompt")
        clear_chat_data(context)
        await update.effective_message.reply_text(f"Skipped {config['item_name']} for today.")
        return ConversationHandler.END

    async def cancel_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel prompt."""
        chat_id = update.effective_chat.id
        logger.info(f"[User:{chat_id}] Cancelled {prompt_type} prompt")
        clear_chat_data(context)
        await update.effective_message.reply_text(f"{prompt_type.replace('_', ' ').title()} cancelled.")
        return ConversationHandler.END

    async def timeout_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle conversation timeout."""
        logger.info(f"{prompt_type} prompt timed out")
        clear_chat_data(context)
        if update and update.effective_message:
            await update.effective_message.reply_text(
                f"{prompt_type.replace('_', ' ').title()} prompt timed out. "
                f"Use /{config['command']} to try again."
            )
        return ConversationHandler.END

    # Build conversation handler
    skip_command = f"skip_{config['command']}"

    handler = ConversationHandler(
        entry_points=[CommandHandler(config['command'], start_prompt)],
        states={
            COLLECTING: [
                CommandHandler('done', done_items),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item),
            ],
            ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout_prompt)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_prompt),
            CommandHandler(skip_command, skip_prompt),
        ],
        conversation_timeout=TIMEOUT_SECONDS,
    )

    # Also return a standalone skip handler for use outside conversation
    skip_standalone = CommandHandler(skip_command, skip_prompt)

    return handler, skip_standalone


# Create handlers for each prompt type
gratitude_handler, skip_gratitude_handler = create_prompt_handlers('gratitude')
themeoftheday_handler, skip_themeoftheday_handler = create_prompt_handlers('themeoftheday')
selflove_handler, skip_selflove_handler = create_prompt_handlers('selflove')
affirmation_handler, skip_affirmation_handler = create_prompt_handlers('affirmation')

# Backward compatibility alias
theme_handler = themeoftheday_handler


async def my_prompts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's daily prompts for today."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        today = get_user_local_date(user)

        # Get today's prompts
        gratitude = Gratitude.get_for_date(session, user.id, today)
        theme = ThemeOfTheDay.get_for_date(session, user.id, today)
        selflove = SelfLove.get_for_date(session, user.id, today)
        affirmation = Affirmation.get_for_date(session, user.id, today)

        lines = [f"<b>Daily Reflections - {readable_date(today)}</b>\n"]

        if gratitude:
            lines.append("<b>Grateful for:</b>")
            lines.append(display_items(gratitude.content, separator="\n"))
            lines.append("")

        if theme:
            lines.append(f"<b>Today's Theme:</b> {theme.content}")
            if theme.reminder_count:
                lines.append(f"(Reminded {theme.reminder_count} time(s))")
            lines.append("")

        if affirmation:
            lines.append("<b>Affirmations:</b>")
            lines.append(display_items(affirmation.content, separator="\n"))
            lines.append("")

        if selflove:
            lines.append("<b>Self-Love:</b>")
            lines.append(display_items(selflove.content, separator="\n"))
            lines.append("")

        if not (gratitude or theme or selflove or affirmation):
            lines.append("No prompts answered yet today.")
            lines.append("\nUse /gratitude, /themeoftheday, /affirmation, or /selflove to start!")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


async def my_affirmations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's recent affirmations."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        # Get recent affirmations (last 7 days)
        affirmations = session.query(Affirmation).filter(
            Affirmation.user_id == user.id
        ).order_by(Affirmation.prompt_date.desc()).limit(7).all()

        if not affirmations:
            await update.effective_message.reply_text(
                "No affirmations recorded yet.\n\n"
                "Use /affirmation to set your daily affirmations!"
            )
            return

        lines = ["<b>Your Recent Affirmations</b>\n"]

        for aff in affirmations:
            lines.append(f"<b>{readable_date(aff.prompt_date)}:</b>")
            lines.append(display_items(aff.content, separator="\n"))
            lines.append("")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


async def my_gratitude(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's recent gratitude entries."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        # Get recent gratitude entries (last 7 days)
        entries = session.query(Gratitude).filter(
            Gratitude.user_id == user.id
        ).order_by(Gratitude.prompt_date.desc()).limit(7).all()

        if not entries:
            await update.effective_message.reply_text(
                "No gratitude entries recorded yet.\n\n"
                "Use /gratitude to log what you're grateful for!"
            )
            return

        lines = ["<b>Your Recent Gratitude Entries</b>\n"]

        for entry in entries:
            lines.append(f"<b>{readable_date(entry.prompt_date)}:</b>")
            lines.append(display_items(entry.content, separator="\n"))
            lines.append("")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


async def my_theme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's recent theme of the day entries."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        # Get recent themes (last 7 days)
        entries = session.query(ThemeOfTheDay).filter(
            ThemeOfTheDay.user_id == user.id
        ).order_by(ThemeOfTheDay.prompt_date.desc()).limit(7).all()

        if not entries:
            await update.effective_message.reply_text(
                "No themes recorded yet.\n\n"
                "Use /themeoftheday to set your daily theme!"
            )
            return

        lines = ["<b>Your Recent Themes</b>\n"]

        for entry in entries:
            lines.append(f"<b>{readable_date(entry.prompt_date)}:</b> {entry.content}")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


async def my_selflove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's recent self-love entries."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        # Get recent self-love entries (last 7 days)
        entries = session.query(SelfLove).filter(
            SelfLove.user_id == user.id
        ).order_by(SelfLove.prompt_date.desc()).limit(7).all()

        if not entries:
            await update.effective_message.reply_text(
                "No self-love entries recorded yet.\n\n"
                "Use /selflove to log things you love about yourself!"
            )
            return

        lines = ["<b>Your Recent Self-Love Entries</b>\n"]

        for entry in entries:
            lines.append(f"<b>{readable_date(entry.prompt_date)}:</b>")
            lines.append(display_items(entry.content, separator="\n"))
            lines.append("")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")
