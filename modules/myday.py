"""
/myday - Factual summary of all logged data for today.

Requires python-telegram-bot v21+
"""
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import func, desc

from dbhelper import Session
from models import (
    User, Wakesleep, Food, Water, Gym, Yoga,
    Pranayam, Thought, Task, Gratitude, ThemeOfTheDay, SelfLove, Affirmation
)
from core.scheduler import get_user_local_date
from utils.logger import get_logger
from utils.formatters import (
    readable_datetime, readable_time, readable_date,
    display_items, format_duration, format_gym_sets, truncate_text
)
from modules.getcurrentuser import get_current_user

logger = get_logger(__name__)


async def myday(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show factual summary of today's logged data."""
    chat_id = update.message.chat_id
    logger.info(f"[User:{chat_id}] Requesting myday summary")

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return

        # Get user's local date
        today = get_user_local_date(user)

        sections = []

        # Header
        sections.append(f"<b>My Day - {today.strftime('%A, %d %B %Y')}</b>")

        has_data = False

        # === DAILY PROMPTS ===
        prompts_section = []

        gratitude = Gratitude.get_for_date(session, user.id, today)
        if gratitude:
            items = display_items(gratitude.content, separator="\n  - ")
            prompts_section.append(f"<b>Grateful for:</b>\n  - {items}")
            has_data = True

        theme = ThemeOfTheDay.get_for_date(session, user.id, today)
        if theme:
            prompts_section.append(f"<b>Today's Theme:</b> {theme.content}")
            if theme.reminder_count:
                prompts_section.append(f"  (Reminded {theme.reminder_count} time(s))")
            has_data = True

        affirmation = Affirmation.get_for_date(session, user.id, today)
        if affirmation:
            items = display_items(affirmation.content, separator="\n  - ")
            prompts_section.append(f"<b>Affirmations:</b>\n  - {items}")
            has_data = True

        selflove = SelfLove.get_for_date(session, user.id, today)
        if selflove:
            items = display_items(selflove.content, separator="\n  - ")
            prompts_section.append(f"<b>Self-Love:</b>\n  - {items}")
            has_data = True

        if prompts_section:
            sections.append("\n<b>--- Daily Reflections ---</b>")
            sections.extend(prompts_section)

        # === SLEEP ===
        sleep_records = (
            session.query(Wakesleep)
            .filter(Wakesleep.user_id == user.id)
            .filter(func.date(Wakesleep.wakeuptime) == today)
            .order_by(Wakesleep.wakeuptime)
            .all()
        )
        if sleep_records:
            sections.append("\n<b>--- Sleep ---</b>")
            for s in sleep_records:
                duration = format_duration(s.sleeptime, s.wakeuptime)
                sections.append(
                    f"Slept: {readable_datetime(s.sleeptime)} - {readable_time(s.wakeuptime)} ({duration})"
                )
                if s.notes:
                    sections.append(f"  Notes: {truncate_text(s.notes, 100)}")
            has_data = True

        # === FOOD ===
        food_records = (
            session.query(Food)
            .filter(Food.user_id == user.id)
            .filter(func.date(Food.food_time) == today)
            .order_by(Food.food_time)
            .all()
        )
        if food_records:
            sections.append("\n<b>--- Meals ---</b>")
            for f in food_records:
                items = display_items(f.food_item)
                label = f.food_label.replace('_', ' ').title()
                sections.append(f"{label} ({readable_time(f.food_time)}): {items}")
                if f.food_notes:
                    sections.append(f"  Notes: {truncate_text(f.food_notes, 80)}")
            has_data = True

        # === WATER ===
        water_records = (
            session.query(Water)
            .filter(Water.user_id == user.id)
            .filter(func.date(Water.water_time) == today)
            .all()
        )
        if water_records:
            water_total = sum(w.amount_ml for w in water_records)
            glasses = water_total / 250
            sections.append("\n<b>--- Water ---</b>")
            sections.append(f"Total: {water_total}ml ({glasses:.1f} glasses)")
            sections.append(f"Entries: {len(water_records)}")
            has_data = True

        # === GYM ===
        gym_records = (
            session.query(Gym)
            .filter(Gym.user_id == user.id)
            .filter(func.date(Gym.gym_datetime) == today)
            .order_by(Gym.gym_datetime)
            .all()
        )
        if gym_records:
            sections.append("\n<b>--- Workouts ---</b>")
            for g in gym_records:
                gym_type = g.gym_type.replace('_', ' ').title()
                sections.append(f"{gym_type} ({readable_time(g.gym_datetime)}):")
                sets_info = format_gym_sets(g.repetition, g.weight)
                for line in sets_info.split('\n'):
                    sections.append(f"  {line}")
                if g.gym_notes:
                    sections.append(f"  Notes: {truncate_text(g.gym_notes, 80)}")
            has_data = True

        # === YOGA ===
        yoga_records = (
            session.query(Yoga)
            .filter(Yoga.user_id == user.id)
            .filter(func.date(Yoga.yoga_datetime) == today)
            .order_by(Yoga.yoga_datetime)
            .all()
        )
        if yoga_records:
            sections.append("\n<b>--- Yoga ---</b>")
            for y in yoga_records:
                yoga_type = y.yoga_type.replace('_', ' ').title()
                sections.append(f"{yoga_type}: {y.repetition} reps ({readable_time(y.yoga_datetime)})")
                if y.yoga_notes:
                    sections.append(f"  Notes: {truncate_text(y.yoga_notes, 80)}")
            has_data = True

        # === PRANAYAM ===
        pranayam_records = (
            session.query(Pranayam)
            .filter(Pranayam.user_id == user.id)
            .filter(func.date(Pranayam.pranayam_datetime) == today)
            .order_by(Pranayam.pranayam_datetime)
            .all()
        )
        if pranayam_records:
            sections.append("\n<b>--- Pranayam ---</b>")
            for p in pranayam_records:
                pranayam_type = p.pranayam_type.replace('_', ' ').title()
                sections.append(f"{pranayam_type}: {p.repetition} reps ({readable_time(p.pranayam_datetime)})")
                if p.pranayam_notes:
                    sections.append(f"  Notes: {truncate_text(p.pranayam_notes, 80)}")
            has_data = True

        # === THOUGHTS ===
        thought_records = (
            session.query(Thought)
            .filter(Thought.user_id == user.id)
            .filter(func.date(Thought.created_at) == today)
            .order_by(Thought.created_at)
            .all()
        )
        if thought_records:
            sections.append("\n<b>--- Thoughts ---</b>")
            for t in thought_records:
                content = display_items(t.content)
                preview = truncate_text(content, 150)
                sections.append(f"- {preview}")
            has_data = True

        # === TASKS ===
        task_records = (
            session.query(Task)
            .filter(Task.user_id == user.id)
            .filter(func.date(Task.created_at) == today)
            .order_by(Task.created_at)
            .all()
        )
        if task_records:
            sections.append("\n<b>--- Completed Tasks ---</b>")
            for t in task_records:
                content = display_items(t.content)
                preview = truncate_text(content, 100)
                sections.append(f"[x] {preview}")
            has_data = True

        # === EMPTY STATE ===
        if not has_data:
            sections.append("\nNo activities logged yet today.")
            sections.append("\nUse /rundown to start logging your day!")

        # Send the summary
        message = '\n'.join(sections)

        # Split if too long (Telegram limit is 4096)
        if len(message) > 4000:
            # Send in chunks
            chunks = []
            current_chunk = ""
            for line in sections:
                if len(current_chunk) + len(line) + 1 > 4000:
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += "\n" + line if current_chunk else line
            if current_chunk:
                chunks.append(current_chunk)

            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode="HTML")
        else:
            await update.message.reply_text(message, parse_mode="HTML")

        logger.info(f"[User:{chat_id}] myday summary sent")
