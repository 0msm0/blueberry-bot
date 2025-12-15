"""
Scheduler for timezone-aware daily prompts and reminders.
Uses python-telegram-bot's JobQueue which wraps APScheduler.

Requires python-telegram-bot v21+
"""
from datetime import datetime, time, timedelta
from typing import Optional, List

import pytz
from telegram.ext import ContextTypes

from dbhelper import Session
from models import User, UserSettings, Gratitude, ThemeOfTheDay, SelfLove, Affirmation
from utils.logger import get_logger

logger = get_logger(__name__)

# Prompt type to model mapping
PROMPT_MODELS = {
    'gratitude': Gratitude,
    'themeoftheday': ThemeOfTheDay,
    'selflove': SelfLove,
    'affirmation': Affirmation,
}

# Theme reminder offsets (hours after theme is set)
THEME_REMINDER_OFFSETS = [3, 6, 9]  # 10:30 AM, 1:30 PM, 4:30 PM if theme set at 7:30

# Prompt messages
PROMPT_MESSAGES = {
    'gratitude': (
        "Good morning! What are the top 3 things you are grateful for today?\n\n"
        "Use /gratitude to answer, or /skip to skip."
    ),
    'themeoftheday': (
        "What is your theme for today?\n\n"
        "This could be a focus area, intention, or goal.\n"
        "Use /themeoftheday to set it, or /skip to skip.\n\n"
        "I'll remind you about your theme 3 times during the day!"
    ),
    'affirmation': (
        "Time for your daily affirmations!\n\n"
        "What positive statements do you want to affirm today?\n"
        "Use /affirmation to set them, or /skip to skip."
    ),
    'selflove': (
        "Good evening! Write 3 things you love about yourself.\n\n"
        "Take a moment to appreciate who you are.\n"
        "Use /selflove to answer, or /skip to skip."
    ),
}


def get_user_timezone(user: User) -> Optional[pytz.BaseTzInfo]:
    """Get user's pytz timezone object."""
    tz_record = user.get_current_timezone()
    if not tz_record:
        return None
    try:
        return pytz.timezone(tz_record.timezone_name)
    except pytz.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {tz_record.timezone_name}")
        return None


def get_user_local_time(user: User) -> Optional[datetime]:
    """Get current datetime in user's timezone."""
    user_tz = get_user_timezone(user)
    if not user_tz:
        return None
    return datetime.now(user_tz)


def get_user_local_date(user: User):
    """Get current date in user's timezone."""
    local_time = get_user_local_time(user)
    if local_time:
        return local_time.date()
    return datetime.now().date()


def parse_time_string(time_str: str) -> tuple:
    """Parse time string like '07:30' to (hour, minute) tuple."""
    parts = time_str.split(':')
    return int(parts[0]), int(parts[1])


def schedule_daily_prompts_for_user(job_queue, user: User, session) -> None:
    """Schedule all daily prompts for a specific user based on their settings."""
    user_tz = get_user_timezone(user)
    if not user_tz:
        logger.warning(f"Cannot schedule prompts for user {user.id}: no timezone")
        return

    # Get or create user settings
    settings = UserSettings.get_or_create(session, user.id)
    schedule = settings.get_schedule_dict()

    for prompt_type, config in schedule.items():
        job_name = f"prompt_{prompt_type}_{user.chat_id}"

        # Remove existing job if any
        remove_job_by_name(job_queue, job_name)

        if not config['enabled']:
            logger.debug(f"Prompt {prompt_type} disabled for user {user.id}")
            continue

        # Parse time string
        hour, minute = parse_time_string(config['time'])
        local_time = time(hour=hour, minute=minute, tzinfo=user_tz)

        try:
            # Schedule the job to run daily at the specified local time
            job_queue.run_daily(
                callback=send_daily_prompt,
                time=local_time,
                days=(0, 1, 2, 3, 4, 5, 6),  # Every day
                data={
                    'chat_id': user.chat_id,
                    'user_id': user.id,
                    'prompt_type': prompt_type,
                },
                name=job_name,
            )
            logger.info(f"Scheduled {prompt_type} for user {user.id} at {local_time} {user_tz}")
        except Exception as e:
            logger.error(f"Error scheduling {prompt_type} for user {user.id}: {e}")


def schedule_daily_prompts_for_all_users(job_queue) -> None:
    """Schedule daily prompts for all users with timezones set."""
    logger.info("Scheduling daily prompts for all users...")

    with Session() as session:
        users = User.get_all(session)
        scheduled_count = 0

        for user in users:
            if user.get_current_timezone():
                schedule_daily_prompts_for_user(job_queue, user, session)
                scheduled_count += 1

        logger.info(f"Scheduled prompts for {scheduled_count} users")


def reschedule_user_prompts(job_queue, user: User, session) -> None:
    """Reschedule prompts for a user (call after settings change)."""
    # Cancel all existing prompt jobs for this user
    for prompt_type in PROMPT_MODELS.keys():
        remove_job_by_name(job_queue, f"prompt_{prompt_type}_{user.chat_id}")

    # Reschedule with new settings
    schedule_daily_prompts_for_user(job_queue, user, session)


def schedule_theme_reminders(job_queue, user: User, theme_content: str, session) -> List[str]:
    """
    Schedule 3 theme reminders after theme is set.
    Returns list of scheduled job names.
    """
    user_tz = get_user_timezone(user)
    if not user_tz:
        return []

    # Check if theme reminders are enabled
    settings = UserSettings.get_or_create(session, user.id)
    if not settings.theme_reminders_enabled:
        logger.debug(f"Theme reminders disabled for user {user.id}")
        return []

    job_ids = []
    now = datetime.now(user_tz)
    today = now.date()

    # Cancel any existing theme reminders for today
    for i in range(1, 4):
        remove_job_by_name(job_queue, f"theme_reminder_{user.chat_id}_{today}_{i}")

    for i, hours_offset in enumerate(THEME_REMINDER_OFFSETS, 1):
        reminder_time = now + timedelta(hours=hours_offset)

        # Only schedule if reminder is still in the future and same day
        if reminder_time > now and reminder_time.date() == today:
            job_name = f"theme_reminder_{user.chat_id}_{today}_{i}"

            try:
                job_queue.run_once(
                    callback=send_theme_reminder,
                    when=reminder_time,
                    data={
                        'chat_id': user.chat_id,
                        'user_id': user.id,
                        'reminder_number': i,
                        'theme_content': theme_content,
                    },
                    name=job_name,
                )
                job_ids.append(job_name)
                logger.info(f"Scheduled theme reminder {i} for user {user.id} at {reminder_time}")
            except Exception as e:
                logger.error(f"Error scheduling theme reminder {i} for user {user.id}: {e}")

    return job_ids


def remove_job_by_name(job_queue, job_name: str) -> bool:
    """Remove a job by its name."""
    jobs = job_queue.get_jobs_by_name(job_name)
    for job in jobs:
        job.schedule_removal()
    return len(jobs) > 0


async def send_daily_prompt(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback to send a daily prompt to user."""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    prompt_type = job_data['prompt_type']
    user_id = job_data['user_id']

    logger.debug(f"Sending {prompt_type} prompt to user {user_id}")

    # Check if already answered today
    with Session() as session:
        user = User.get_by_id(session, user_id)
        if not user:
            logger.warning(f"User {user_id} not found for daily prompt")
            return

        today = get_user_local_date(user)
        model = PROMPT_MODELS.get(prompt_type)

        if model and model.exists_for_date(session, user_id, today):
            logger.debug(f"User {user_id} already answered {prompt_type} for {today}")
            return

    # Send the prompt
    message = PROMPT_MESSAGES.get(prompt_type, "Daily prompt")

    try:
        await context.bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Sent {prompt_type} prompt to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending {prompt_type} prompt to user {user_id}: {e}")


async def send_theme_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback to send a theme reminder."""
    job_data = context.job.data
    chat_id = job_data['chat_id']
    user_id = job_data['user_id']
    reminder_number = job_data['reminder_number']
    theme_content = job_data['theme_content']

    logger.debug(f"Sending theme reminder {reminder_number} to user {user_id}")

    reminder_texts = {
        1: f"Reminder #{reminder_number}: Your theme for today is:\n\n\"{theme_content}\"\n\nHow's it going?",
        2: f"Midday check-in! Remember your theme:\n\n\"{theme_content}\"",
        3: f"Afternoon reminder! Your theme today:\n\n\"{theme_content}\"\n\nKeep it up!",
    }

    message = reminder_texts.get(reminder_number, f"Theme reminder: {theme_content}")

    try:
        await context.bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Sent theme reminder {reminder_number} to user {user_id}")

        # Update reminder count in database
        with Session() as session:
            user = User.get_by_id(session, user_id)
            if user:
                today = get_user_local_date(user)
                theme = ThemeOfTheDay.get_for_date(session, user_id, today)
                if theme:
                    theme.reminder_count = reminder_number
                    session.commit()

    except Exception as e:
        logger.error(f"Error sending theme reminder to user {user_id}: {e}")


def cancel_theme_reminders_for_user(job_queue, user: User) -> int:
    """Cancel all pending theme reminders for a user. Returns count of cancelled jobs."""
    user_tz = get_user_timezone(user)
    if not user_tz:
        return 0

    today = datetime.now(user_tz).date()
    cancelled = 0

    for i in range(1, 4):
        if remove_job_by_name(job_queue, f"theme_reminder_{user.chat_id}_{today}_{i}"):
            cancelled += 1

    return cancelled
