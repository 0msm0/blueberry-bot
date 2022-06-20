from telegram.ext import CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, inlinequeryhandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from models import User, Timezone
from dbhelper import Session
import logging
from modules.getcurrentuser import get_current_user


log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def clear_userdata(context):
    context.user_data.clear()
    logger.info(f"user_data cleared")


def clear_chatdata(context):
    context.chat_data.clear()
    logger.info(f"chat_data cleared")