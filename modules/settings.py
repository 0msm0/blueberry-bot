"""
User settings management for daily prompt schedules.

Requires python-telegram-bot v21+
"""
import re
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
from models import User, UserSettings
from core.scheduler import reschedule_user_prompts
from utils.logger import get_logger
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data

logger = get_logger(__name__)

# Conversation states
SELECT_SETTING, SET_TIME, CONFIRM_TOGGLE = range(3)

# Timeout
TIMEOUT_SECONDS = 300

# Prompt display names
PROMPT_NAMES = {
    'gratitude': 'Gratitude',
    'themeoftheday': 'Theme of the Day',
    'affirmation': 'Affirmation',
    'selflove': 'Self-Love',
}


def format_time_12h(time_str: str) -> str:
    """Convert 24h time string to 12h format for display."""
    hour, minute = time_str.split(':')
    hour = int(hour)
    period = 'AM' if hour < 12 else 'PM'
    if hour == 0:
        hour = 12
    elif hour > 12:
        hour -= 12
    return f"{hour}:{minute} {period}"


def parse_time_input(text: str) -> str:
    """
    Parse user time input and return 24h format string.
    Accepts: 7:30, 07:30, 7:30 AM, 7:30am, 19:30, etc.
    Returns None if invalid.
    """
    text = text.strip().lower()

    # Remove spaces around colon
    text = re.sub(r'\s*:\s*', ':', text)

    # Pattern for time with optional AM/PM
    match = re.match(r'^(\d{1,2}):(\d{2})\s*(am|pm)?$', text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2))
    period = match.group(3)

    # Validate minute
    if minute < 0 or minute > 59:
        return None

    # Handle AM/PM
    if period:
        if hour < 1 or hour > 12:
            return None
        if period == 'am' and hour == 12:
            hour = 0
        elif period == 'pm' and hour != 12:
            hour += 12
    else:
        # 24-hour format
        if hour < 0 or hour > 23:
            return None

    return f"{hour:02d}:{minute:02d}"


def get_settings_keyboard():
    """Generate settings menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("Gratitude Time", callback_data="set_gratitude")],
        [InlineKeyboardButton("Theme of the Day Time", callback_data="set_themeoftheday")],
        [InlineKeyboardButton("Affirmation Time", callback_data="set_affirmation")],
        [InlineKeyboardButton("Self-Love Time", callback_data="set_selflove")],
        [InlineKeyboardButton("Theme Reminders: Toggle", callback_data="toggle_theme_reminders")],
        [InlineKeyboardButton("Done", callback_data="settings_done")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_toggle_keyboard(prompt_type: str, current_enabled: bool):
    """Generate toggle keyboard for enabling/disabling a prompt."""
    status = "ON" if current_enabled else "OFF"
    new_status = "OFF" if current_enabled else "ON"
    keyboard = [
        [InlineKeyboardButton(f"Turn {new_status}", callback_data=f"toggle_{prompt_type}")],
        [InlineKeyboardButton("Back", callback_data="back_to_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def format_settings_message(settings: UserSettings) -> str:
    """Format current settings for display."""
    schedule = settings.get_schedule_dict()

    lines = ["<b>Daily Prompt Settings</b>\n"]
    lines.append("Configure when you receive daily prompts.\n")

    for prompt_type, config in schedule.items():
        name = PROMPT_NAMES.get(prompt_type, prompt_type)
        time_12h = format_time_12h(config['time'])
        status = "ON" if config['enabled'] else "OFF"
        lines.append(f"<b>{name}:</b> {time_12h} [{status}]")

    # Theme reminders
    reminders_status = "ON" if settings.theme_reminders_enabled else "OFF"
    lines.append(f"\n<b>Theme Reminders:</b> {reminders_status}")
    lines.append("(3 reminders after theme is set)")

    lines.append("\nSelect an option to modify:")
    return "\n".join(lines)


async def start_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /settings command."""
    chat_id = update.message.chat_id
    logger.info(f"[User:{chat_id}] Opening settings")

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

        settings = UserSettings.get_or_create(session, user.id)

        message = format_settings_message(settings)
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard()
        )

    return SELECT_SETTING


async def handle_setting_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle settings menu button presses."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data == "settings_done":
        await query.edit_message_text("Settings saved!")
        clear_chat_data(context)
        return ConversationHandler.END

    if data == "back_to_menu":
        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                settings = UserSettings.get_or_create(session, user.id)
                message = format_settings_message(settings)
                await query.edit_message_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=get_settings_keyboard()
                )
        return SELECT_SETTING

    if data == "toggle_theme_reminders":
        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                settings = UserSettings.get_or_create(session, user.id)
                settings.theme_reminders_enabled = not settings.theme_reminders_enabled
                session.commit()

                status = "enabled" if settings.theme_reminders_enabled else "disabled"
                await query.edit_message_text(
                    f"Theme reminders {status}!\n\n"
                    f"Returning to settings...",
                    parse_mode="HTML"
                )

                # Show updated settings
                message = format_settings_message(settings)
                await query.message.reply_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=get_settings_keyboard()
                )
        return SELECT_SETTING

    if data.startswith("set_"):
        prompt_type = data[4:]  # Remove "set_" prefix
        context.chat_data['editing_prompt'] = prompt_type

        name = PROMPT_NAMES.get(prompt_type, prompt_type)

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                settings = UserSettings.get_or_create(session, user.id)
                schedule = settings.get_schedule_dict()
                current_time = schedule[prompt_type]['time']
                current_enabled = schedule[prompt_type]['enabled']

                status = "ON" if current_enabled else "OFF"

                keyboard = [
                    [InlineKeyboardButton(
                        f"Turn {'OFF' if current_enabled else 'ON'}",
                        callback_data=f"toggle_enable_{prompt_type}"
                    )],
                    [InlineKeyboardButton("Back", callback_data="back_to_menu")],
                ]

                await query.edit_message_text(
                    f"<b>{name}</b>\n\n"
                    f"Current time: {format_time_12h(current_time)}\n"
                    f"Status: {status}\n\n"
                    f"Send a new time (e.g., 7:30 AM or 19:30)\n"
                    f"Or use the buttons below:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        return SET_TIME

    if data.startswith("toggle_enable_"):
        prompt_type = data[14:]  # Remove "toggle_enable_" prefix

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                settings = UserSettings.get_or_create(session, user.id)

                # Toggle the enabled flag
                attr_name = f"{prompt_type}_enabled"
                current = getattr(settings, attr_name)
                setattr(settings, attr_name, not current)
                session.commit()

                # Reschedule prompts
                if context.job_queue:
                    reschedule_user_prompts(context.job_queue, user, session)

                status = "enabled" if not current else "disabled"
                name = PROMPT_NAMES.get(prompt_type, prompt_type)

                await query.edit_message_text(f"{name} prompts {status}!")

                # Show updated settings menu
                message = format_settings_message(settings)
                await query.message.reply_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=get_settings_keyboard()
                )

        return SELECT_SETTING

    return SELECT_SETTING


async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time input from user."""
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    prompt_type = context.chat_data.get('editing_prompt')

    if not prompt_type:
        await update.message.reply_text("Error: No prompt selected. Use /settings to start again.")
        clear_chat_data(context)
        return ConversationHandler.END

    # Parse time
    parsed_time = parse_time_input(text)
    if not parsed_time:
        await update.message.reply_text(
            "Invalid time format. Please use:\n"
            "- 7:30 AM or 7:30 PM\n"
            "- 07:30 or 19:30 (24-hour)\n\n"
            "Try again or tap Back to return to menu."
        )
        return SET_TIME

    # Save the new time
    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        settings = UserSettings.get_or_create(session, user.id)

        # Update the time
        attr_name = f"{prompt_type}_time"
        setattr(settings, attr_name, parsed_time)
        session.commit()

        # Reschedule prompts
        if context.job_queue:
            reschedule_user_prompts(context.job_queue, user, session)

        name = PROMPT_NAMES.get(prompt_type, prompt_type)

        await update.message.reply_text(
            f"{name} time set to {format_time_12h(parsed_time)}!"
        )

        # Show updated settings menu
        message = format_settings_message(settings)
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=get_settings_keyboard()
        )

    clear_chat_data(context)
    return SELECT_SETTING


async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel settings."""
    chat_id = update.effective_chat.id
    logger.info(f"[User:{chat_id}] Cancelled settings")
    clear_chat_data(context)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Settings cancelled.")
    else:
        await update.effective_message.reply_text("Settings cancelled.")

    return ConversationHandler.END


async def timeout_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle settings timeout."""
    logger.info("Settings timed out")
    clear_chat_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Settings timed out. Use /settings to try again."
        )
    return ConversationHandler.END


# Build conversation handler
settings_handler = ConversationHandler(
    entry_points=[CommandHandler('settings', start_settings)],
    states={
        SELECT_SETTING: [
            CallbackQueryHandler(handle_setting_selection),
        ],
        SET_TIME: [
            CallbackQueryHandler(handle_setting_selection),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input),
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout_settings),
            CallbackQueryHandler(timeout_settings),
        ],
    },
    fallbacks=[
        CommandHandler('cancel', cancel_settings),
    ],
    conversation_timeout=TIMEOUT_SECONDS,
)
