"""
Blueberry Bot - Personal Wellness Tracking Telegram Bot

Main entry point for the bot application.
Supports both polling (development) and webhook (production) modes.

Requires python-telegram-bot v21+
"""
import os
import asyncio

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from dbhelper import init_database
from bot_commands import BOT_COMMANDS, get_help_text
from utils.logger import get_logger

# Import conversation handlers
from modules.registration import registration_handler
from modules.timezone import set_timezone_handler, my_timezone
from modules.wakesleep import wakesleep_handler, my_sleep
from modules.food import food_handler, my_food
from modules.water import water_handler, my_water
from modules.gym import gym_handler, my_gym
from modules.yoga import yoga_handler, my_yoga
from modules.pranayam import pranayam_handler, my_pranayam
from modules.thought import thoughts_handler, my_thoughts
from modules.taskcompleted import taskcompleted_handler, my_tasks
from modules.dailyprompts import (
    gratitude_handler, themeoftheday_handler, selflove_handler,
    affirmation_handler, my_prompts, my_affirmations,
    my_gratitude, my_theme, my_selflove
)
from modules.settings import settings_handler
from modules.rundown import rundown_handler
from modules.myday import myday
from modules.goals import goals_handler, mygoals
from modules.affirmation_lists import affirmation_lists_handler, my_affirmation_lists

# Import scheduler
from core.scheduler import schedule_daily_prompts_for_all_users

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger(__name__)

# Bot configuration
BOT_TOKEN = os.environ.get("bot_token")
TG_MODE = os.environ.get("TG_MODE", "polling").lower()
WEBHOOK_URL = os.environ.get("LIVE_SERVER_URL", "")
PORT = int(os.environ.get("PORT", 8443))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - Welcome message."""
    user_name = update.effective_user.first_name or "there"

    welcome_text = (
        f"Hey {user_name}! Welcome to Blueberry Bot.\n\n"
        f"I help you track your daily wellness activities:\n"
        f"- Sleep patterns\n"
        f"- Meals & Water intake\n"
        f"- Workouts\n"
        f"- Yoga & Pranayam\n"
        f"- Thoughts & Tasks\n\n"
        f"<b>Quick Start:</b>\n"
        f"1. /register - Create your account\n"
        f"2. /set_timezone - Set your timezone\n"
        f"3. Start logging with /sleep, /food, /water, /gym, etc.\n\n"
        f"Use /help to see all commands."
    )

    await update.message.reply_text(welcome_text, parse_mode="HTML")
    logger.info(f"Start command from user: {update.effective_user.id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - Show available commands."""
    await update.message.reply_text(get_help_text(), parse_mode="HTML")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for the bot."""
    # Get user info for logging
    user_id = "Unknown"
    chat_id = "Unknown"

    if isinstance(update, Update):
        if update.effective_user:
            user_id = update.effective_user.id
        if update.effective_chat:
            chat_id = update.effective_chat.id

    # Log detailed error information
    logger.error(
        f"[User:{user_id}] [Chat:{chat_id}] Error: {type(context.error).__name__}: {context.error}",
        exc_info=context.error
    )

    # Log the update that caused the error (for debugging)
    if isinstance(update, Update):
        if update.message:
            logger.debug(f"Error triggered by message: {update.message.text}")
        elif update.callback_query:
            logger.debug(f"Error triggered by callback: {update.callback_query.data}")

        # Try to notify user if possible
        if update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "An error occurred. Please try again or use /cancel to start fresh."
                )
            except Exception:
                pass


async def setup_commands(application: Application) -> None:
    """Set up bot commands for the Telegram menu."""
    commands = [
        BotCommand(cmd, desc)
        for cmd, desc in BOT_COMMANDS.items()
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set up successfully")


def register_handlers(application: Application) -> None:
    """Register all handlers with the application."""
    # Conversation handlers (must be added before command handlers)
    application.add_handler(registration_handler)
    application.add_handler(set_timezone_handler)
    application.add_handler(wakesleep_handler)
    application.add_handler(food_handler)
    application.add_handler(water_handler)
    application.add_handler(gym_handler)
    application.add_handler(yoga_handler)
    application.add_handler(pranayam_handler)
    application.add_handler(thoughts_handler)
    application.add_handler(taskcompleted_handler)

    # Daily prompts conversation handlers
    application.add_handler(gratitude_handler)
    application.add_handler(themeoftheday_handler)
    application.add_handler(selflove_handler)
    application.add_handler(affirmation_handler)

    # Settings handler
    application.add_handler(settings_handler)

    # Goals and affirmation lists handlers
    application.add_handler(goals_handler)
    application.add_handler(affirmation_lists_handler)

    # Smart check-in handlers
    application.add_handler(rundown_handler)

    # Basic command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # View history command handlers
    application.add_handler(CommandHandler("mytimezone", my_timezone))
    application.add_handler(CommandHandler("mysleep", my_sleep))
    application.add_handler(CommandHandler("mywakesleep", my_sleep))  # Backwards compat
    application.add_handler(CommandHandler("myfood", my_food))
    application.add_handler(CommandHandler("mywater", my_water))
    application.add_handler(CommandHandler("mygym", my_gym))
    application.add_handler(CommandHandler("myyoga", my_yoga))
    application.add_handler(CommandHandler("mypranayam", my_pranayam))
    application.add_handler(CommandHandler("mythoughts", my_thoughts))
    application.add_handler(CommandHandler("mythought", my_thoughts))  # Backwards compat
    application.add_handler(CommandHandler("mytasks", my_tasks))
    application.add_handler(CommandHandler("mytaskcompleted", my_tasks))  # Backwards compat
    application.add_handler(CommandHandler("myprompts", my_prompts))
    application.add_handler(CommandHandler("myaffirmations", my_affirmations))
    application.add_handler(CommandHandler("mygratitude", my_gratitude))
    application.add_handler(CommandHandler("mytheme", my_theme))
    application.add_handler(CommandHandler("myselflove", my_selflove))
    application.add_handler(CommandHandler("mygoals", mygoals))
    application.add_handler(CommandHandler("myaffirmationlists", my_affirmation_lists))

    # Summary command
    application.add_handler(CommandHandler("myday", myday))

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("All handlers registered successfully")


async def post_init(application: Application) -> None:
    """Post-initialization hook - runs after application is initialized."""
    # Set up bot commands
    await setup_commands(application)

    # Initialize scheduler for daily prompts
    logger.info("Initializing daily prompts scheduler...")
    schedule_daily_prompts_for_all_users(application.job_queue)


def main() -> None:
    """Main entry point."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        raise ValueError("BOT_TOKEN environment variable is required")

    logger.info("Initializing Blueberry Bot...")

    # Initialize database
    logger.info("Initializing database...")
    init_database()

    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register handlers
    register_handlers(application)

    # Run bot based on mode
    if TG_MODE == "webhook":
        logger.info(f"Starting bot in webhook mode on port {PORT}...")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
        )
    else:
        logger.info("Starting bot in polling mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
