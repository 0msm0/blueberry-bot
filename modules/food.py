"""
Food logging conversation handler.
Requires python-telegram-bot v21+
"""
import os
from datetime import datetime

import requests
from telegram import Update, constants
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
from models import User, Food
from utils.logger import get_logger
from utils.keyboards import (
    generate_minute_keyboard,
    make_markup,
    DATE_KEYBOARD,
    HOUR_KEYBOARD,
    FOOD_LABEL_KEYBOARD,
)
from utils.patterns import DATE_PATTERN, HOUR_PATTERN, MINUTE_PATTERN, FOOD_LABEL_PATTERN
from utils.formatters import (
    readable_datetime,
    parse_date_selection,
    combine_date_time,
    join_items,
    display_items,
)
from modules.getcurrentuser import get_user_with_timezone
from modules.helpers import clear_chat_data, append_to_chat_data_list

logger = get_logger(__name__)

# Conversation states
DATE, HOUR, MINUTE, ITEMS, NOTES, PHOTOS, LABEL = range(7)

# Configuration
TIMEOUT_SECONDS = 600  # 10 minutes
PHOTOS_DIR = "userfoods"

# Ensure photos directory exists
if not os.path.isdir(PHOTOS_DIR):
    os.makedirs(PHOTOS_DIR)


async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for food logging."""
    chat_id = update.message.chat_id
    logger.info(f"[User:{chat_id}] Starting food logging")

    with Session() as session:
        user = await get_user_with_timezone(chat_id, update, context, session)
        if not user:
            logger.warning(f"[User:{chat_id}] Food logging aborted - user not found or no timezone")
            return ConversationHandler.END

    context.chat_data.clear()
    await update.message.reply_text(
        "Let's log your meal.\n\n"
        "Use /cancel to cancel anytime."
    )
    await update.message.reply_text(
        "When did you eat?",
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
            "Please use /food again and select a recent date."
        )
        return ConversationHandler.END

    context.chat_data['food_date'] = parse_date_selection(query.data)

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
    context.chat_data['food_hour'] = hour

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
    food_datetime = combine_date_time(
        context.chat_data['food_date'],
        time_str
    )
    context.chat_data['food_time'] = food_datetime

    await query.edit_message_text(
        f"Time: {readable_datetime(food_datetime)}\n\n"
        "Now enter what you ate.\n"
        "Send each item as a separate message.\n\n"
        "Use /done when finished."
    )
    return ITEMS


async def handle_food_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle food item input."""
    item = update.message.text.strip()
    append_to_chat_data_list(context, 'food_items', item)
    count = len(context.chat_data.get('food_items', []))
    await update.message.reply_text(f"✓ Added: {item}\n\nSend more items or /done when finished.")
    return ITEMS


async def done_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish adding food items."""
    items = context.chat_data.get('food_items', [])

    if not items:
        await update.message.reply_text("Please add at least one food item.")
        return ITEMS

    await update.message.reply_text(
        f"Items: {', '.join(items)}\n\n"
        "Any notes? (or /skip)"
    )
    return NOTES


async def handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle notes input."""
    chat_id = update.effective_chat.id
    notes = update.message.text.strip()
    context.chat_data['food_notes'] = notes
    logger.debug(f"[User:{chat_id}] Food notes added: {notes[:50]}...")

    await update.message.reply_text(
        "Upload photos of your food (optional).\n\n"
        "Send photos or use /skip_photos to skip."
    )
    return PHOTOS


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip notes."""
    chat_id = update.effective_chat.id
    logger.debug(f"[User:{chat_id}] Skipping food notes")
    context.chat_data['food_notes'] = ""

    await update.message.reply_text(
        "Upload photos of your food (optional).\n\n"
        "Send photos or use /skip_photos to skip."
    )
    logger.debug(f"[User:{chat_id}] Transitioning to PHOTOS state")
    return PHOTOS


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo upload."""
    try:
        photo = update.message.photo[-1]  # Get highest resolution
        file_id = photo.file_id
        file = await photo.get_file()
        file_path = file.file_path

        # Download and save
        ext = file_path.split('.')[-1] if '.' in file_path else 'jpg'
        filename = f"{file_id}.{ext}"
        local_path = os.path.join(PHOTOS_DIR, filename)

        response = requests.get(file_path)
        with open(local_path, 'wb') as f:
            f.write(response.content)

        append_to_chat_data_list(context, 'food_photos', local_path)
        await update.message.reply_text("Photo saved! Add more or use /done.")

    except Exception as e:
        logger.error(f"Error saving photo: {e}", exc_info=True)
        await update.message.reply_text("Error uploading photo. Try again or use /done.")

    return PHOTOS


async def handle_non_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle non-photo input during photo state."""
    await update.message.reply_text("Please send a photo or use /done to continue.")
    return PHOTOS


async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish photo uploads and select label."""
    await update.message.reply_text(
        "What type of meal was this?",
        reply_markup=make_markup(FOOD_LABEL_KEYBOARD)
    )
    return LABEL


async def skip_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip photos via command."""
    chat_id = update.effective_chat.id
    logger.debug(f"[User:{chat_id}] Skipping photos")

    await update.message.reply_text(
        "What type of meal was this?",
        reply_markup=make_markup(FOOD_LABEL_KEYBOARD)
    )
    return LABEL


async def handle_label(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle meal label selection and save."""
    query = update.callback_query
    await query.answer()

    context.chat_data['food_label'] = query.data
    await query.delete_message()

    return await save_food_record(update, context)


async def save_food_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save food record to database."""
    chat_id = update.effective_chat.id
    chat_data = context.chat_data

    logger.debug(f"[User:{chat_id}] Saving food record. chat_data keys: {list(chat_data.keys())}")

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            logger.error(f"[User:{chat_id}] User not found when saving food record")
            await update.effective_message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        food_time = chat_data.get('food_time')
        food_items = join_items(chat_data.get('food_items', []))
        food_notes = chat_data.get('food_notes', '')
        food_photos = join_items(chat_data.get('food_photos', []))
        food_label = chat_data.get('food_label', 'other')

        logger.debug(f"[User:{chat_id}] Food data - time: {food_time}, items: {food_items[:50]}..., label: {food_label}")

        record = Food(
            user_id=user.id,
            food_time=food_time,
            food_item=food_items,
            food_notes=food_notes,
            food_photos=food_photos if food_photos else None,
            food_label=food_label,
            created_at=datetime.now()
        )

        try:
            session.add(record)
            session.commit()

            logger.info(f"Food record saved: {record}")

            await update.effective_message.reply_text(
                f"Meal logged!\n\n"
                f"<b>Time:</b> {readable_datetime(record.food_time)}\n"
                f"<b>Items:</b> {display_items(record.food_item)}\n"
                f"<b>Label:</b> {record.food_label}\n"
                f"<b>Notes:</b> {record.food_notes or '-'}",
                parse_mode="HTML"
            )
            await update.effective_message.reply_text(
                "Use /myfood to view your food history."
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving food record: {e}", exc_info=True)
            await update.effective_message.reply_text(
                "Error saving food record. Please try /food again."
            )
        finally:
            clear_chat_data(context)

    return ConversationHandler.END


async def my_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's food history."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        records = (
            session.query(Food)
            .filter(Food.user_id == user.id)
            .order_by(desc(Food.food_time))
            .limit(5)
            .all()
        )

        if records:
            for i, record in enumerate(records):
                text = (
                    f"{i+1}. {readable_datetime(record.food_time)} - "
                    f"{record.food_label}\n"
                    f"{display_items(record.food_item)}"
                )
                await update.effective_message.reply_text(text)

                # Send photo if available
                if record.food_photos:
                    photos = record.food_photos.split(",,,")
                    for photo_path in photos[:1]:  # Send first photo only
                        try:
                            if os.path.exists(photo_path):
                                with open(photo_path, 'rb') as f:
                                    await update.effective_message.reply_photo(photo=f)
                        except Exception as e:
                            logger.error(f"Error sending photo: {e}")
        else:
            await update.effective_message.reply_text(
                "No food records yet. Use /food to log your first meal!"
            )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel food logging."""
    logger.info("Food logging cancelled")
    clear_chat_data(context)
    await update.effective_message.reply_text("Food logging cancelled.")
    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    logger.info("Food logging timed out")
    clear_chat_data(context)
    await update.effective_message.reply_text(
        "Food logging timed out. Please use /food to try again."
    )
    return ConversationHandler.END


# Build the conversation handler
food_handler = ConversationHandler(
    entry_points=[CommandHandler('food', food)],
    states={
        DATE: [CallbackQueryHandler(handle_date, pattern=DATE_PATTERN)],
        HOUR: [CallbackQueryHandler(handle_hour, pattern=HOUR_PATTERN)],
        MINUTE: [CallbackQueryHandler(handle_minute, pattern=MINUTE_PATTERN)],
        ITEMS: [
            CommandHandler('done', done_items),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_food_item)
        ],
        NOTES: [
            CommandHandler('skip', skip_notes),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notes)
        ],
        PHOTOS: [
            CommandHandler('done', done_photos),
            CommandHandler('skip_photos', skip_photos),
            MessageHandler(filters.PHOTO, handle_photo),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_non_photo)
        ],
        LABEL: [CallbackQueryHandler(handle_label, pattern=FOOD_LABEL_PATTERN)],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout)]
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
        CommandHandler('cancelfood', cancel),  # Backwards compatibility
    ],
    conversation_timeout=TIMEOUT_SECONDS
)

# Export for main.py
myfood = my_food
