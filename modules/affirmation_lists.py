"""
Affirmation Lists management - CRUD operations for categorized affirmations.

Commands:
- /affirmationlists - Main menu for managing affirmation lists
- /myaffirmationlists - Quick view of all lists

Note: /affirmation is the daily prompt command (in dailyprompts.py).
This module handles the persistent affirmation library/lists feature.

Requires python-telegram-bot v21+
"""
from datetime import datetime

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
from models import User, AffirmationCategory, AffirmationListItem
from utils.logger import get_logger
from utils.formatters import join_items, display_items
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data, append_to_chat_data_list

logger = get_logger(__name__)

# Conversation states
MENU = 0
SELECT_CATEGORY = 1
SELECT_LIST = 2
VIEW_LIST = 3
ENTER_TITLE = 4
ENTER_ITEMS = 5
CONFIRM_DELETE = 6
ENTER_CATEGORY_NAME = 7
EDIT_LIST = 8

TIMEOUT_SECONDS = 600


def get_main_menu_keyboard():
    """Generate main menu keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("View Lists", callback_data="view_lists")],
        [InlineKeyboardButton("Create New List", callback_data="create_list")],
        [InlineKeyboardButton("Manage Categories", callback_data="manage_categories")],
        [InlineKeyboardButton("Done", callback_data="done")],
    ])


def get_category_keyboard(categories, action_prefix="cat", include_back=True):
    """Generate category selection keyboard."""
    keyboard = []
    for cat in categories:
        icon = "" if cat.is_predefined else ""
        keyboard.append([InlineKeyboardButton(
            f"{icon} {cat.display_name}",
            callback_data=f"{action_prefix}_{cat.id}"
        )])
    if include_back:
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


def get_list_keyboard(lists, include_back=True):
    """Generate list selection keyboard."""
    keyboard = []
    for lst in lists:
        keyboard.append([InlineKeyboardButton(
            lst.title,
            callback_data=f"list_{lst.id}"
        )])
    if include_back:
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_categories")])
    return InlineKeyboardMarkup(keyboard)


def get_list_actions_keyboard(list_id):
    """Generate actions keyboard for a specific list."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Edit", callback_data=f"edit_{list_id}")],
        [InlineKeyboardButton("Delete", callback_data=f"delete_{list_id}")],
        [InlineKeyboardButton("Back", callback_data="back_to_lists")],
    ])


def get_category_management_keyboard(categories):
    """Generate category management keyboard."""
    keyboard = [[InlineKeyboardButton("Add Custom Category", callback_data="add_category")]]

    # Add delete buttons for custom categories only
    custom_cats = [c for c in categories if not c.is_predefined]
    for cat in custom_cats:
        keyboard.append([InlineKeyboardButton(
            f"Delete: {cat.display_name}",
            callback_data=f"delcat_{cat.id}"
        )])

    keyboard.append([InlineKeyboardButton("Back", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(keyboard)


async def affirmation_lists_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /affirmationlists command."""
    chat_id = update.message.chat_id
    logger.info(f"[User:{chat_id}] Opening affirmation lists menu")

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if not user:
            return ConversationHandler.END

        # Ensure predefined categories exist for this user
        existing = AffirmationCategory.get_all_for_user(session, user.id)
        if not existing:
            AffirmationCategory.create_predefined_for_user(session, user.id)
            session.commit()

    context.chat_data.clear()
    await update.message.reply_text(
        "<b>Affirmation Lists</b>\n\n"
        "Manage your categorized affirmation lists.\n"
        "Build your personal library of affirmations!",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )
    return MENU


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu button presses."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data == "done":
        await query.edit_message_text("Affirmation lists closed.")
        clear_chat_data(context)
        return ConversationHandler.END

    if data == "back_to_menu":
        await query.edit_message_text(
            "<b>Affirmation Lists</b>\n\n"
            "Manage your categorized affirmation lists.\n"
            "Build your personal library of affirmations!",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU

    if data == "view_lists" or data == "create_list":
        context.chat_data['action'] = 'view' if data == "view_lists" else 'create'

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if not user:
                await query.edit_message_text("Error: User not found.")
                return ConversationHandler.END

            categories = AffirmationCategory.get_all_for_user(session, user.id)

            action_text = "view" if data == "view_lists" else "add a list to"
            await query.edit_message_text(
                f"<b>Select a Category</b>\n\n"
                f"Choose a category to {action_text}:",
                parse_mode="HTML",
                reply_markup=get_category_keyboard(categories, action_prefix="cat")
            )
        return SELECT_CATEGORY

    if data == "manage_categories":
        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                categories = AffirmationCategory.get_all_for_user(session, user.id)

                lines = ["<b>Manage Categories</b>\n"]
                lines.append("<b>Predefined:</b>")
                for cat in categories:
                    if cat.is_predefined:
                        lines.append(f"  {cat.display_name}")

                custom = [c for c in categories if not c.is_predefined]
                if custom:
                    lines.append("\n<b>Custom:</b>")
                    for cat in custom:
                        lines.append(f"  {cat.display_name}")

                await query.edit_message_text(
                    "\n".join(lines),
                    parse_mode="HTML",
                    reply_markup=get_category_management_keyboard(categories)
                )
        return MENU

    if data == "add_category":
        await query.edit_message_text(
            "<b>Add Custom Category</b>\n\n"
            "Enter a name for your new category:\n"
            "(e.g., \"Morning Routine\", \"Confidence\", \"Abundance\")\n\n"
            "Send the name or /cancel to go back."
        )
        return ENTER_CATEGORY_NAME

    if data.startswith("delcat_"):
        cat_id = int(data[7:])
        context.chat_data['delete_category_id'] = cat_id

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                # Check if category has lists
                lists = AffirmationListItem.get_by_category(session, cat_id)

                if lists:
                    await query.edit_message_text(
                        f"This category has {len(lists)} list(s).\n"
                        f"Deleting the category will also delete all its lists.\n\n"
                        f"Are you sure?",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("Yes, Delete", callback_data="confirm_delcat")],
                            [InlineKeyboardButton("Cancel", callback_data="manage_categories")],
                        ])
                    )
                else:
                    # Delete immediately if no lists
                    cat = session.query(AffirmationCategory).filter(
                        AffirmationCategory.id == cat_id,
                        AffirmationCategory.user_id == user.id
                    ).first()
                    if cat:
                        session.delete(cat)
                        session.commit()
                        await query.edit_message_text(f"Category deleted!")

                    # Show updated category list
                    categories = AffirmationCategory.get_all_for_user(session, user.id)
                    await query.message.reply_text(
                        "<b>Manage Categories</b>",
                        parse_mode="HTML",
                        reply_markup=get_category_management_keyboard(categories)
                    )
        return MENU

    if data == "confirm_delcat":
        cat_id = context.chat_data.get('delete_category_id')
        if cat_id:
            with Session() as session:
                user = User.get_user_by_chat_id(session, chat_id)
                if user:
                    cat = session.query(AffirmationCategory).filter(
                        AffirmationCategory.id == cat_id,
                        AffirmationCategory.user_id == user.id
                    ).first()
                    if cat:
                        session.delete(cat)
                        session.commit()
                        logger.info(f"[User:{chat_id}] Deleted category {cat_id}")

                    await query.edit_message_text("Category and its lists deleted!")

                    categories = AffirmationCategory.get_all_for_user(session, user.id)
                    await query.message.reply_text(
                        "<b>Manage Categories</b>",
                        parse_mode="HTML",
                        reply_markup=get_category_management_keyboard(categories)
                    )
        return MENU

    return MENU


async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle category selection."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data == "back_to_menu":
        await query.edit_message_text(
            "<b>Affirmation Lists</b>\n\n"
            "Manage your categorized affirmation lists.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
        return MENU

    if data.startswith("cat_"):
        cat_id = int(data[4:])
        context.chat_data['category_id'] = cat_id
        action = context.chat_data.get('action', 'view')

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if not user:
                await query.edit_message_text("Error: User not found.")
                return ConversationHandler.END

            category = session.query(AffirmationCategory).filter(
                AffirmationCategory.id == cat_id
            ).first()

            if not category:
                await query.edit_message_text("Error: Category not found.")
                return SELECT_CATEGORY

            if action == 'create':
                context.chat_data['category_name'] = category.display_name
                await query.edit_message_text(
                    f"<b>Create List in {category.display_name}</b>\n\n"
                    f"Enter a title for your new list:\n"
                    f"(e.g., \"Morning affirmations\", \"Before sleep\")\n\n"
                    f"Send the title or /cancel to go back.",
                    parse_mode="HTML"
                )
                return ENTER_TITLE

            else:  # view
                lists = AffirmationListItem.get_by_category(session, cat_id)

                if not lists:
                    await query.edit_message_text(
                        f"<b>{category.display_name}</b>\n\n"
                        f"No lists in this category yet.\n"
                        f"Use 'Create New List' to add one!",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("Create List", callback_data="create_in_cat")],
                            [InlineKeyboardButton("Back", callback_data="back_to_menu")],
                        ])
                    )
                    return SELECT_CATEGORY

                await query.edit_message_text(
                    f"<b>{category.display_name}</b>\n\n"
                    f"Select a list to view:",
                    parse_mode="HTML",
                    reply_markup=get_list_keyboard(lists)
                )
                return SELECT_LIST

    if data == "create_in_cat":
        cat_id = context.chat_data.get('category_id')
        if cat_id:
            with Session() as session:
                category = session.query(AffirmationCategory).filter(
                    AffirmationCategory.id == cat_id
                ).first()
                if category:
                    context.chat_data['category_name'] = category.display_name
                    await query.edit_message_text(
                        f"<b>Create List in {category.display_name}</b>\n\n"
                        f"Enter a title for your new list:",
                        parse_mode="HTML"
                    )
                    return ENTER_TITLE

    return SELECT_CATEGORY


async def handle_list_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle list selection."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data == "back_to_categories":
        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                categories = AffirmationCategory.get_all_for_user(session, user.id)
                await query.edit_message_text(
                    "<b>Select a Category</b>",
                    parse_mode="HTML",
                    reply_markup=get_category_keyboard(categories)
                )
        return SELECT_CATEGORY

    if data.startswith("list_"):
        list_id = int(data[5:])
        context.chat_data['list_id'] = list_id

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if not user:
                return ConversationHandler.END

            lst = AffirmationListItem.get_by_id_and_user(session, list_id, user.id)
            if not lst:
                await query.edit_message_text("Error: List not found.")
                return SELECT_LIST

            items = display_items(lst.items, separator="\n")

            await query.edit_message_text(
                f"<b>{lst.title}</b>\n"
                f"<i>({lst.category.display_name})</i>\n\n"
                f"{items}",
                parse_mode="HTML",
                reply_markup=get_list_actions_keyboard(list_id)
            )
        return VIEW_LIST

    return SELECT_LIST


async def handle_list_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle list view actions (edit/delete)."""
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    data = query.data

    if data == "back_to_lists":
        cat_id = context.chat_data.get('category_id')
        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user and cat_id:
                lists = AffirmationListItem.get_by_category(session, cat_id)
                category = session.query(AffirmationCategory).filter(
                    AffirmationCategory.id == cat_id
                ).first()

                await query.edit_message_text(
                    f"<b>{category.display_name if category else 'Lists'}</b>\n\n"
                    f"Select a list to view:",
                    parse_mode="HTML",
                    reply_markup=get_list_keyboard(lists)
                )
        return SELECT_LIST

    if data.startswith("edit_"):
        list_id = int(data[5:])
        context.chat_data['editing_list_id'] = list_id
        context.chat_data['items'] = []

        with Session() as session:
            user = User.get_user_by_chat_id(session, chat_id)
            if user:
                lst = AffirmationListItem.get_by_id_and_user(session, list_id, user.id)
                if lst:
                    await query.edit_message_text(
                        f"<b>Edit: {lst.title}</b>\n\n"
                        f"Current items:\n{display_items(lst.items, separator=chr(10))}\n\n"
                        f"Send new affirmations one by one.\n"
                        f"Use /done when finished or /cancel to discard changes.",
                        parse_mode="HTML"
                    )
                    return EDIT_LIST

    if data.startswith("delete_"):
        list_id = int(data[7:])
        context.chat_data['delete_list_id'] = list_id

        await query.edit_message_text(
            "Are you sure you want to delete this list?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Yes, Delete", callback_data="confirm_delete")],
                [InlineKeyboardButton("Cancel", callback_data=f"list_{list_id}")],
            ])
        )
        return VIEW_LIST

    if data == "confirm_delete":
        list_id = context.chat_data.get('delete_list_id')
        if list_id:
            with Session() as session:
                user = User.get_user_by_chat_id(session, chat_id)
                if user:
                    lst = AffirmationListItem.get_by_id_and_user(session, list_id, user.id)
                    if lst:
                        cat_id = lst.category_id
                        session.delete(lst)
                        session.commit()
                        logger.info(f"[User:{chat_id}] Deleted affirmation list {list_id}")

                        await query.edit_message_text("List deleted!")

                        # Go back to category's list view
                        lists = AffirmationListItem.get_by_category(session, cat_id)
                        category = session.query(AffirmationCategory).filter(
                            AffirmationCategory.id == cat_id
                        ).first()

                        if lists:
                            await query.message.reply_text(
                                f"<b>{category.display_name if category else 'Lists'}</b>",
                                parse_mode="HTML",
                                reply_markup=get_list_keyboard(lists)
                            )
                            return SELECT_LIST
                        else:
                            await query.message.reply_text(
                                "No more lists in this category.",
                                reply_markup=get_main_menu_keyboard()
                            )
                            return MENU

    return VIEW_LIST


async def handle_title_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle list title input."""
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text:
        await update.message.reply_text("Title cannot be empty. Please enter a title:")
        return ENTER_TITLE

    if len(text) > 100:
        await update.message.reply_text("Title is too long (max 100 characters). Please shorten it.")
        return ENTER_TITLE

    context.chat_data['list_title'] = text
    context.chat_data['items'] = []

    cat_name = context.chat_data.get('category_name', 'this category')
    await update.message.reply_text(
        f"<b>Creating: {text}</b>\n"
        f"<i>in {cat_name}</i>\n\n"
        f"Now send your affirmations one by one.\n"
        f"Use /done when finished (minimum 1 item).",
        parse_mode="HTML"
    )
    return ENTER_ITEMS


async def handle_item_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle affirmation item input."""
    text = update.message.text.strip()

    if not text:
        await update.message.reply_text("Affirmation cannot be empty. Please enter an affirmation:")
        return ENTER_ITEMS

    if len(text) > 500:
        await update.message.reply_text("Item is too long (max 500 characters). Please shorten it.")
        return ENTER_ITEMS

    append_to_chat_data_list(context, 'items', text)
    count = len(context.chat_data.get('items', []))

    await update.message.reply_text(
        f"Added! ({count} item{'s' if count > 1 else ''})\n"
        f"Send more or /done to finish."
    )
    return ENTER_ITEMS


async def handle_edit_item_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle affirmation item input during edit."""
    text = update.message.text.strip()

    if not text:
        await update.message.reply_text("Affirmation cannot be empty. Please enter an affirmation:")
        return EDIT_LIST

    if len(text) > 500:
        await update.message.reply_text("Item is too long (max 500 characters). Please shorten it.")
        return EDIT_LIST

    append_to_chat_data_list(context, 'items', text)
    count = len(context.chat_data.get('items', []))

    await update.message.reply_text(
        f"Added! ({count} new item{'s' if count > 1 else ''})\n"
        f"Send more or /done to save changes."
    )
    return EDIT_LIST


async def done_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish adding items and save list."""
    items = context.chat_data.get('items', [])
    chat_id = update.effective_chat.id

    if not items:
        await update.message.reply_text("Please add at least one affirmation.")
        return ENTER_ITEMS

    cat_id = context.chat_data.get('category_id')
    title = context.chat_data.get('list_title')

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        lst = AffirmationListItem(
            user_id=user.id,
            category_id=cat_id,
            title=title,
            items=join_items(items),
            created_at=datetime.now()
        )

        try:
            session.add(lst)
            session.commit()
            logger.info(f"[User:{chat_id}] Created affirmation list: {title}")

            await update.message.reply_text(
                f"<b>List Created: {title}</b>\n\n"
                f"{display_items(lst.items, separator=chr(10))}",
                parse_mode="HTML"
            )
            await update.message.reply_text(
                "What would you like to do next?",
                reply_markup=get_main_menu_keyboard()
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating list: {e}", exc_info=True)
            await update.message.reply_text("Error saving list. Please try again.")

        finally:
            clear_chat_data(context)

    return MENU


async def done_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finish editing and save changes."""
    items = context.chat_data.get('items', [])
    chat_id = update.effective_chat.id
    list_id = context.chat_data.get('editing_list_id')

    if not items:
        await update.message.reply_text("Please add at least one affirmation.")
        return EDIT_LIST

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.message.reply_text("Error: User not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        lst = AffirmationListItem.get_by_id_and_user(session, list_id, user.id)
        if not lst:
            await update.message.reply_text("Error: List not found.")
            clear_chat_data(context)
            return ConversationHandler.END

        try:
            lst.items = join_items(items)
            lst.updated_at = datetime.now()
            session.commit()
            logger.info(f"[User:{chat_id}] Updated affirmation list: {lst.title}")

            await update.message.reply_text(
                f"<b>List Updated: {lst.title}</b>\n\n"
                f"{display_items(lst.items, separator=chr(10))}",
                parse_mode="HTML"
            )
            await update.message.reply_text(
                "What would you like to do next?",
                reply_markup=get_main_menu_keyboard()
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating list: {e}", exc_info=True)
            await update.message.reply_text("Error saving changes. Please try again.")

        finally:
            clear_chat_data(context)

    return MENU


async def handle_category_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom category name input."""
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text:
        await update.message.reply_text("Category name cannot be empty. Please enter a name:")
        return ENTER_CATEGORY_NAME

    if len(text) > 50:
        await update.message.reply_text("Category name is too long (max 50 characters).")
        return ENTER_CATEGORY_NAME

    # Create slug from name
    name_slug = text.lower().replace(" ", "-")

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.message.reply_text("Error: User not found.")
            return MENU

        # Check if category already exists
        existing = AffirmationCategory.get_by_user_and_name(session, user.id, name_slug)
        if existing:
            await update.message.reply_text(
                f"A category named '{text}' already exists.\n"
                f"Please choose a different name."
            )
            return ENTER_CATEGORY_NAME

        category = AffirmationCategory(
            user_id=user.id,
            name=name_slug,
            display_name=text,
            is_predefined=0
        )
        session.add(category)
        session.commit()
        logger.info(f"[User:{chat_id}] Created category: {text}")

        await update.message.reply_text(f"Category '{text}' created!")

        # Show updated category management
        categories = AffirmationCategory.get_all_for_user(session, user.id)
        await update.message.reply_text(
            "<b>Manage Categories</b>",
            parse_mode="HTML",
            reply_markup=get_category_management_keyboard(categories)
        )

    return MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation."""
    chat_id = update.effective_chat.id
    logger.info(f"[User:{chat_id}] Cancelled affirmation lists")
    clear_chat_data(context)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled.")
    else:
        await update.effective_message.reply_text("Cancelled.")

    return ConversationHandler.END


async def timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timeout."""
    logger.info("Affirmation lists timed out")
    clear_chat_data(context)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Session timed out. Use /affirmationlists to continue."
        )
    return ConversationHandler.END


async def my_affirmation_lists(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick view of all affirmation lists."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if not user:
            await update.effective_message.reply_text("Please /register first.")
            return

        categories = AffirmationCategory.get_all_for_user(session, user.id)

        if not categories:
            await update.effective_message.reply_text(
                "No affirmation lists yet.\n\n"
                "Use /affirmationlists to create your first list!"
            )
            return

        lines = ["<b>Your Affirmation Lists</b>\n"]

        has_lists = False
        for cat in categories:
            lists = AffirmationListItem.get_by_category(session, cat.id)
            if lists:
                has_lists = True
                icon = "" if cat.is_predefined else ""
                lines.append(f"\n<b>{icon} {cat.display_name}</b>")
                for lst in lists:
                    item_count = len(lst.items_list)
                    lines.append(f"  - {lst.title} ({item_count} items)")

        if not has_lists:
            lines.append("No lists created yet.")
            lines.append("\nUse /affirmationlists to create your first list!")
        else:
            lines.append("\nUse /affirmationlists to manage your lists.")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


# Conversation handler
affirmation_lists_handler = ConversationHandler(
    entry_points=[CommandHandler('affirmationlists', affirmation_lists_menu)],
    states={
        MENU: [
            CallbackQueryHandler(handle_menu_selection),
        ],
        SELECT_CATEGORY: [
            CallbackQueryHandler(handle_category_selection),
        ],
        SELECT_LIST: [
            CallbackQueryHandler(handle_list_selection),
        ],
        VIEW_LIST: [
            CallbackQueryHandler(handle_list_actions),
        ],
        ENTER_TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title_input),
        ],
        ENTER_ITEMS: [
            CommandHandler('done', done_items),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_input),
        ],
        EDIT_LIST: [
            CommandHandler('done', done_edit),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_item_input),
        ],
        ENTER_CATEGORY_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_name_input),
        ],
        ConversationHandler.TIMEOUT: [
            MessageHandler(filters.ALL, timeout),
            CallbackQueryHandler(timeout),
        ],
    },
    fallbacks=[
        CommandHandler('cancel', cancel),
    ],
    conversation_timeout=TIMEOUT_SECONDS,
)
