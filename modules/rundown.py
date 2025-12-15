"""
/rundown - Smart daily check-in that shows logged items and guides through missing ones.

Requires python-telegram-bot v21+
"""
from datetime import datetime
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from sqlalchemy import func

from dbhelper import Session
from models import (
    User, Wakesleep, Food, Water, Gym, Yoga,
    Pranayam, Thought, Task, Gratitude, ThemeOfTheDay, SelfLove, Affirmation
)
from core.scheduler import get_user_local_date
from utils.logger import get_logger
from utils.formatters import (
    readable_time, display_items, format_duration,
    join_items, truncate_text
)
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data, append_to_chat_data_list

logger = get_logger(__name__)

# Conversation states
SHOW_STATUS, ASK_CONTINUE, COLLECTING = range(3)

TIMEOUT_SECONDS = 900  # 15 minutes for full rundown

# Items to check in order with display names
RUNDOWN_ORDER = [
    'sleep',
    'food',
    'water',
    'gym',
    'yoga',
    'pranayam',
    'thought',
    'task',
    'gratitude',
    'themeoftheday',
    'affirmation',
    'selflove',
]

ITEM_DISPLAY_NAMES = {
    'sleep': 'Sleep',
    'food': 'Food',
    'water': 'Water',
    'gym': 'Gym',
    'yoga': 'Yoga',
    'pranayam': 'Pranayam',
    'thought': 'Thoughts',
    'task': 'Tasks',
    'gratitude': 'Gratitude',
    'themeoftheday': 'Theme of the Day',
    'affirmation': 'Affirmation',
    'selflove': 'Self-Love',
}

ITEM_PROMPTS = {
    'sleep': "When did you wake up today? (e.g., 6:30)",
    'food': "What did you eat? Send items, then /done",
    'water': "How much water? (e.g., 500ml or 2 glasses)",
    'gym': "What workout did you do? (e.g., biceps, chest)",
    'yoga': "What yoga did you practice?",
    'pranayam': "What pranayam did you do?",
    'thought': "What's on your mind? Send thoughts, then /done",
    'task': "What tasks did you complete? Send items, then /done",
    'gratitude': "What are 3 things you're grateful for? Send items, then /done",
    'themeoftheday': "What's your theme/intention for today?",
    'affirmation': "What positive affirmations for today? Send items, then /done",
    'selflove': "What are 3 things you love about yourself? Send items, then /done",
}

# Items that need multiple inputs
MULTI_INPUT_ITEMS = ['food', 'thought', 'task', 'gratitude', 'affirmation', 'selflove']

# Mapping for prompt models
PROMPT_MODELS = {
    'gratitude': Gratitude,
    'themeoftheday': ThemeOfTheDay,
    'affirmation': Affirmation,
    'selflove': SelfLove,
}


def get_today_status(session, user: User, today) -> Dict[str, dict]:
    """
    Get status of all items for today.
    Returns dict with 'logged' bool and 'summary' string for each item.
    """
    status = {}

    # Sleep
    sleep_records = (
        session.query(Wakesleep)
        .filter(Wakesleep.user_id == user.id)
        .filter(func.date(Wakesleep.wakeuptime) == today)
        .all()
    )
    if sleep_records:
        last = sleep_records[-1]
        duration = format_duration(last.sleeptime, last.wakeuptime)
        status['sleep'] = {'logged': True, 'summary': duration}
    else:
        status['sleep'] = {'logged': False, 'summary': None}

    # Food
    food_records = (
        session.query(Food)
        .filter(Food.user_id == user.id)
        .filter(func.date(Food.food_time) == today)
        .all()
    )
    if food_records:
        labels = [f.food_label.replace('_', ' ').title() for f in food_records]
        status['food'] = {'logged': True, 'summary': ', '.join(labels)}
    else:
        status['food'] = {'logged': False, 'summary': None}

    # Water
    water_total = (
        session.query(func.sum(Water.amount_ml))
        .filter(Water.user_id == user.id)
        .filter(func.date(Water.water_time) == today)
        .scalar()
    ) or 0
    if water_total:
        glasses = water_total / 250
        status['water'] = {'logged': True, 'summary': f'{water_total}ml ({glasses:.1f} glasses)'}
    else:
        status['water'] = {'logged': False, 'summary': None}

    # Gym
    gym_records = (
        session.query(Gym)
        .filter(Gym.user_id == user.id)
        .filter(func.date(Gym.gym_datetime) == today)
        .all()
    )
    if gym_records:
        types = [g.gym_type.replace('_', ' ').title() for g in gym_records]
        status['gym'] = {'logged': True, 'summary': ', '.join(types)}
    else:
        status['gym'] = {'logged': False, 'summary': None}

    # Yoga
    yoga_records = (
        session.query(Yoga)
        .filter(Yoga.user_id == user.id)
        .filter(func.date(Yoga.yoga_datetime) == today)
        .all()
    )
    if yoga_records:
        types = [y.yoga_type.replace('_', ' ').title() for y in yoga_records]
        status['yoga'] = {'logged': True, 'summary': ', '.join(types)}
    else:
        status['yoga'] = {'logged': False, 'summary': None}

    # Pranayam
    pranayam_records = (
        session.query(Pranayam)
        .filter(Pranayam.user_id == user.id)
        .filter(func.date(Pranayam.pranayam_datetime) == today)
        .all()
    )
    if pranayam_records:
        types = [p.pranayam_type.replace('_', ' ').title() for p in pranayam_records]
        status['pranayam'] = {'logged': True, 'summary': ', '.join(types)}
    else:
        status['pranayam'] = {'logged': False, 'summary': None}

    # Thoughts
    thought_records = (
        session.query(Thought)
        .filter(Thought.user_id == user.id)
        .filter(func.date(Thought.created_at) == today)
        .all()
    )
    if thought_records:
        status['thought'] = {'logged': True, 'summary': f'{len(thought_records)} entries'}
    else:
        status['thought'] = {'logged': False, 'summary': None}

    # Tasks
    task_records = (
        session.query(Task)
        .filter(Task.user_id == user.id)
        .filter(func.date(Task.created_at) == today)
        .all()
    )
    if task_records:
        status['task'] = {'logged': True, 'summary': f'{len(task_records)} completed'}
    else:
        status['task'] = {'logged': False, 'summary': None}

    # Daily Prompts - using new separate models
    gratitude = Gratitude.get_for_date(session, user.id, today)
    if gratitude:
        preview = truncate_text(gratitude.content, 40)
        status['gratitude'] = {'logged': True, 'summary': preview}
    else:
        status['gratitude'] = {'logged': False, 'summary': None}

    theme = ThemeOfTheDay.get_for_date(session, user.id, today)
    if theme:
        preview = truncate_text(theme.content, 40)
        status['themeoftheday'] = {'logged': True, 'summary': preview}
    else:
        status['themeoftheday'] = {'logged': False, 'summary': None}

    affirmation = Affirmation.get_for_date(session, user.id, today)
    if affirmation:
        preview = truncate_text(affirmation.content, 40)
        status['affirmation'] = {'logged': True, 'summary': preview}
    else:
        status['affirmation'] = {'logged': False, 'summary': None}

    selflove = SelfLove.get_for_date(session, user.id, today)
    if selflove:
        preview = truncate_text(selflove.content, 40)
        status['selflove'] = {'logged': True, 'summary': preview}
    else:
        status['selflove'] = {'logged': False, 'summary': None}

    return status


def format_status_message(status: Dict[str, dict]) -> str:
    """Format status dict into readable message."""
    lines = ["<b>Today's Progress:</b>\n"]

    for key in RUNDOWN_ORDER:
        name = ITEM_DISPLAY_NAMES.get(key, key.title())
        item = status.get(key, {'logged': False})

        if item['logged']:
            lines.append(f"[x] <b>{name}:</b> {item['summary']}")
        else:
            lines.append(f"[ ] {name}")

    return '\n'.join(lines)


async def rundown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for rundown command."""
    chat_id = update.message.chat_id
    logger.info(f"[User:{chat_id}] Starting rundown")

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

        # Get user's local date
        today = get_user_local_date(user)

        # Get status of all items
        status = get_today_status(session, user, today)

        # Store in context
        context.chat_data.clear()
        context.chat_data['rundown_status'] = status
        context.chat_data['rundown_date'] = today
        context.chat_data['rundown_user_id'] = user.id

        # Find missing items
        missing = [key for key in RUNDOWN_ORDER if not status[key]['logged']]
        context.chat_data['rundown_missing'] = missing
        context.chat_data['rundown_position'] = 0

        # Show current status
        status_msg = format_status_message(status)
        await update.message.reply_text(status_msg, parse_mode="HTML")

        if not missing:
            await update.message.reply_text(
                "Amazing! You've logged everything for today!\n"
                "Keep up the great work!"
            )
            clear_chat_data(context)
            return ConversationHandler.END

        # Ask if user wants to fill in missing items
        keyboard = [
            [
                InlineKeyboardButton("Fill in missing", callback_data="start_filling"),
                InlineKeyboardButton("Skip for now", callback_data="skip_rundown"),
            ]
        ]

        await update.message.reply_text(
            f"\nYou have {len(missing)} item(s) to log.\n"
            f"Would you like to fill them in now?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ASK_CONTINUE


async def handle_continue_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user's choice to continue or skip."""
    query = update.callback_query
    await query.answer()

    if query.data == "skip_rundown":
        await query.edit_message_text("Okay! Use /rundown anytime to continue.")
        clear_chat_data(context)
        return ConversationHandler.END

    # Start filling missing items
    await query.edit_message_text("Let's fill in the missing items!")
    return await prompt_next_item(update, context)


async def prompt_next_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for the next missing item."""
    missing = context.chat_data.get('rundown_missing', [])
    position = context.chat_data.get('rundown_position', 0)

    if position >= len(missing):
        # All done!
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="All done! You've completed your daily rundown.\n"
                 "Great job! Use /myday to see your full summary."
        )
        clear_chat_data(context)
        return ConversationHandler.END

    current_item = missing[position]
    context.chat_data['rundown_current_item'] = current_item
    context.chat_data['rundown_items'] = []  # For multi-input items

    name = ITEM_DISPLAY_NAMES.get(current_item, current_item.title())
    prompt = ITEM_PROMPTS.get(current_item, f"Enter your {name}:")

    # Add skip button
    keyboard = [[InlineKeyboardButton(f"Skip {name}", callback_data="skip_item")]]

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"({position + 1}/{len(missing)}) <b>{name}</b>\n\n{prompt}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return COLLECTING


async def handle_item_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user input for current item."""
    text = update.message.text.strip()
    current_item = context.chat_data.get('rundown_current_item')

    if not text:
        await update.message.reply_text("Please enter something or use the Skip button.")
        return COLLECTING

    # For multi-input items, collect and wait for /done
    if current_item in MULTI_INPUT_ITEMS:
        append_to_chat_data_list(context, 'rundown_items', text)
        count = len(context.chat_data.get('rundown_items', []))
        await update.message.reply_text(f"Added! ({count} items) Send more or /done to continue.")
        return COLLECTING

    # For single-input items, save immediately
    return await save_current_item(update, context, [text])


async def handle_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /done command for multi-input items."""
    items = context.chat_data.get('rundown_items', [])

    if not items:
        await update.message.reply_text("Please add at least one item first.")
        return COLLECTING

    return await save_current_item(update, context, items)


async def save_current_item(update: Update, context: ContextTypes.DEFAULT_TYPE, items: List[str]) -> int:
    """Save the current item and move to next."""
    current_item = context.chat_data.get('rundown_current_item')
    today = context.chat_data.get('rundown_date')
    user_id = context.chat_data.get('rundown_user_id')

    logger.debug(f"Saving rundown item {current_item}: {items}")

    with Session() as session:
        user = User.get_by_id(session, user_id)
        if not user:
            await update.effective_message.reply_text("Error: User not found.")
            return await advance_to_next(update, context)

        try:
            now = datetime.now()

            # Save based on item type
            if current_item == 'thought':
                record = Thought(
                    user_id=user.id,
                    content=join_items(items),
                    created_at=now
                )
                session.add(record)

            elif current_item == 'task':
                record = Task(
                    user_id=user.id,
                    content=join_items(items),
                    created_at=now
                )
                session.add(record)

            elif current_item in PROMPT_MODELS:
                Model = PROMPT_MODELS[current_item]
                record = Model(
                    user_id=user.id,
                    prompt_date=today,
                    content=join_items(items),
                    created_at=now
                )
                session.add(record)

            elif current_item == 'water':
                # Parse water amount
                amount = parse_water_amount(items[0])
                if amount:
                    record = Water(
                        user_id=user.id,
                        water_time=now,
                        amount_ml=amount,
                        created_at=now
                    )
                    session.add(record)
                else:
                    await update.effective_message.reply_text(
                        "Couldn't parse water amount. Try '500ml' or '2 glasses'.\n"
                        "Skipping water for now."
                    )
                    return await advance_to_next(update, context)

            else:
                # For sleep, food, gym, yoga, pranayam - redirect to dedicated commands
                await update.effective_message.reply_text(
                    f"For {ITEM_DISPLAY_NAMES[current_item]}, please use the dedicated command:\n"
                    f"/{current_item if current_item != 'sleep' else 'sleep'}\n\n"
                    f"Moving to next item..."
                )
                return await advance_to_next(update, context)

            session.commit()
            await update.effective_message.reply_text(f"Saved!")
            logger.info(f"Rundown: saved {current_item} for user {user_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving {current_item}: {e}", exc_info=True)
            await update.effective_message.reply_text(f"Error saving. Skipping...")

    return await advance_to_next(update, context)


def parse_water_amount(text: str) -> Optional[int]:
    """Parse water amount from text like '500ml', '2 glasses', '1L'."""
    text = text.lower().strip()

    # Try parsing as ml
    if 'ml' in text:
        try:
            return int(text.replace('ml', '').strip())
        except ValueError:
            pass

    # Try parsing as liters
    if 'l' in text or 'liter' in text or 'litre' in text:
        try:
            num = text.replace('liters', '').replace('litres', '').replace('liter', '').replace('litre', '').replace('l', '').strip()
            return int(float(num) * 1000)
        except ValueError:
            pass

    # Try parsing as glasses (250ml each)
    if 'glass' in text:
        try:
            num = text.replace('glasses', '').replace('glass', '').strip()
            return int(float(num) * 250)
        except ValueError:
            pass

    # Try parsing as just a number (assume ml)
    try:
        num = int(text)
        if num < 50:  # Likely glasses
            return num * 250
        return num
    except ValueError:
        pass

    return None


async def advance_to_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Move to next missing item."""
    context.chat_data['rundown_position'] = context.chat_data.get('rundown_position', 0) + 1
    context.chat_data['rundown_items'] = []
    return await prompt_next_item(update, context)


async def skip_current_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip current item and move to next."""
    query = update.callback_query
    await query.answer()

    current_item = context.chat_data.get('rundown_current_item', 'item')
    name = ITEM_DISPLAY_NAMES.get(current_item, current_item.title())

    await query.edit_message_text(f"Skipped {name}.")
    return await advance_to_next(update, context)


async def cancel_rundown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel rundown."""
    logger.info("Rundown cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text(
        "Rundown cancelled.\n"
        "Use /rundown to start again anytime."
    )
    return ConversationHandler.END


async def timeout_rundown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Rundown timed out")
    clear_chat_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Rundown timed out.\n"
            "Use /rundown to continue where you left off."
        )
    return ConversationHandler.END


# Build the conversation handler
rundown_handler = ConversationHandler(
    entry_points=[CommandHandler('rundown', rundown)],
    states={
        ASK_CONTINUE: [
            CallbackQueryHandler(handle_continue_choice, pattern="^(start_filling|skip_rundown)$"),
        ],
        COLLECTING: [
            CommandHandler('done', handle_done_command),
            CallbackQueryHandler(skip_current_item, pattern="^skip_item$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_input),
        ],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout_rundown)],
    },
    fallbacks=[
        CommandHandler('cancel', cancel_rundown),
        CommandHandler('skip', lambda u, c: skip_current_item(u, c) if u.callback_query else advance_to_next(u, c)),
    ],
    conversation_timeout=TIMEOUT_SECONDS,
)
