from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, inlinequeryhandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import os
from models import User, Timezone, Wakesleep, Food, Gym, Yoga, Pranayam
from dbhelper import Session, engine
import logging
from modules.food import food_handler, myfood
from modules.registration import registration_handler
from modules.timezone import set_timezone_handler, mytimezone
from modules.wakesleep import wakesleep_handler, mywakesleep
from modules.gym import gym_handler, mygym
from modules.yoga import yoga_handler, myyoga
from modules.pranayam import pranayam_handler, mypranayam
from modules.getcurrentuser import get_current_user

load_dotenv()

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

token = os.environ.get('bot_token')


def start(update: Update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        # update.effective_message.reply_text("What's your timezone?")
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            update.effective_message.reply_text(f"Hey, {user.name}.\n"
                                      f"Try /wakesleep /mywakesleeps /food to start adding your logs.")


def error_callback(update, context):
    try:
        logger.error(f"ERROR from error_callback. Update - {update} caused error {context.error}", exc_info=True)
    except:
        logger.error(f"EXCEPTION from error_callback. Update - {update} caused error {context.error}", exc_info=True)


if __name__ == '__main__':
    User.__table__.create(engine, checkfirst=True)
    Timezone.__table__.create(engine, checkfirst=True)
    Wakesleep.__table__.create(engine, checkfirst=True)
    Food.__table__.create(engine, checkfirst=True)
    Gym.__table__.create(engine, checkfirst=True)
    Yoga.__table__.create(engine, checkfirst=True)
    Pranayam.__table__.create(engine, checkfirst=True)

    updater = Updater(token=token, use_context=True)
    dp: Dispatcher = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('mytimezone', mytimezone))
    dp.add_handler(CommandHandler('mywakesleep', mywakesleep))
    dp.add_handler(CommandHandler('myfood', myfood))
    dp.add_handler(CommandHandler('mygym', mygym))
    dp.add_handler(CommandHandler('myyoga', myyoga))
    dp.add_handler(CommandHandler('mypranayam', mypranayam))
    dp.add_handler(registration_handler)
    dp.add_handler(set_timezone_handler)
    dp.add_handler(wakesleep_handler)
    dp.add_handler(food_handler)
    dp.add_handler(gym_handler)
    dp.add_handler(yoga_handler)
    dp.add_handler(pranayam_handler)
    dp.add_error_handler(error_callback)

    tg_mode = os.environ.get("TG_MODE", "polling")

    if tg_mode == 'webhook':
        ssl_cert_file_loc = os.environ.get("ssl_cert_file_loc", 'error')
        # SSL_CERT = 'certi/ssl-limabot.pem' # we'll create folder on server and ssl certificate on server itself. no need to create it here. but better to mention here.
        live_server_url = os.environ.get("LIVE_SERVER_URL", "0.0.0.0")  # reqd format https://11.11.11.11:443  (no trailing slash) (should be 443 and not 8443)
        logger.info('inside WEBHOOK block')
        updater.start_webhook(listen="0.0.0.0", port=8443, url_path=f"{token}", webhook_url=f"{live_server_url}/{token}", cert=ssl_cert_file_loc)
        logger.info(updater.bot.get_webhook_info())
        updater.idle()
    else:
        logger.info('inside POLLING block')
        updater.start_polling()
        updater.idle()