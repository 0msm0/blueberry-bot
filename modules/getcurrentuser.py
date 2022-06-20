from telegram.ext import CallbackContext
from models import User
import logging

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def get_current_user(chat_id, update, context: CallbackContext, session):
    """ Get current user from context, returns instance of User class. If not, send std message to user """
    user_data = context.user_data
    user = User.get_user_by_chatid(session=session, chat_id=chat_id)
    if user:
        user_data['user'] = user  # TODO REMOVE IF REMAINS UNUSED AT THE END OF THE PROJECT
        logger.info(f"Got user from db and stored to user_data - {user_data['user']} for FUTURE USE if any")
        # if user.timezones.count() == 0:   #TODO this may be call expense so use wisely
        #     update.message.reply_text("You need to /set_timezone before using the bot.")
        return user
    else:
        logger.info(f"User not found. Sent message to register")
        update.message.reply_text(f"Hey, you need to /register first")
        return None