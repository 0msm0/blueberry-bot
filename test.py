from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, inlinequeryhandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import os
from datetime import datetime
load_dotenv()

token = os.environ.get('bot_token')
FIRST, SECOND, THIRD = range(3)

def start(update: Update, context: CallbackContext):
    keyboard = [[
        InlineKeyboardButton("3to4",callback_data="threefour"),
        InlineKeyboardButton("4to5",callback_data="fourfive"),
    ]]
    update.message.reply_text("Select hour first", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return FIRST

def first(update, context):
    query = update.callback_query
    update.callback_query.answer()
    print(query)
    if query.data=='threefour':
        new_key = [[
            InlineKeyboardButton("3.10", callback_data="threeten"),
            InlineKeyboardButton("3.20", callback_data="threetwenty"),
        ]]
        update.callback_query.edit_message_text("Now select minutes", reply_markup=InlineKeyboardMarkup(inline_keyboard=new_key))
        return SECOND
    elif query.data=='fourfive':
        new_key = [[
            InlineKeyboardButton("4.10", callback_data="fourten"),
            InlineKeyboardButton("4.20", callback_data="fourtwenty"),
        ]]
        update.callback_query.edit_message_text("Now select minutes", reply_markup=InlineKeyboardMarkup(inline_keyboard=new_key))
        return SECOND

def second(update, context):
    query = update.callback_query
    update.callback_query.answer()
    if query.data=='threeten':
        update.callback_query.edit_message_text("You got up at 3.10am")
        update.callback_query.message.reply_text("Now add comment")
        return THIRD
    elif query.data=='threetwenty':
        update.callback_query.edit_message_text("You got up at 3.20am")
        update.callback_query.message.reply_text("Now add comment")
        return THIRD
    elif query.data=='fourten':
        update.callback_query.edit_message_text("You got up at 4.10am")
        update.callback_query.message.reply_text("Now add comment")
        return THIRD
    elif query.data=='fourtwenty':
        update.callback_query.edit_message_text("You got up at 4.20am")
        update.callback_query.message.reply_text("Now add comment")
        return THIRD

def third(update, context):
    ans = update.message.text
    update.message.reply_text(f"You entered -> {ans}")
    return ConversationHandler.END


if __name__ == '__main__':
    updater = Updater(token=token)
    dp: Dispatcher = updater.dispatcher
    wakeup_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
                FIRST: [CallbackQueryHandler(first, pattern='^threefour|fourfive')],
                SECOND: [CallbackQueryHandler(second, pattern='^threeten|threetwenty|fourten|fourtwenty$')],
                THIRD: [MessageHandler(Filters.text, third)]
                },
        fallbacks=[],
        # conversation_timeout=wakeup_timeout_time
    )
    dp.add_handler(wakeup_conv)
    updater.start_polling()
    updater.idle()