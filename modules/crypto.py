from telegram.ext import ConversationHandler, CommandHandler, \
    MessageHandler, Filters
from dbhelper import Session
import logging
from models import User, Crypto
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chatdata
from datetime import datetime


log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

crypto_timeout_time = 120
WALLET = range(1)

def crypto(update, context):
    logger.info("Inside crypto")
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            # update.message.reply_text("Let's start. (use /cancelthoughts if you want to cancel)")
            # chat_data = context.chat_data
            update.message.reply_text("You get rewarded RoutineBotToken for adding your logs. \n\nEnter your wallet (polygon below). Click /idonthavewallet if you don't have one.")
            return WALLET


def addwallet(update, context):
    logger.info('enter your wallet')
    chat_data = context.chat_data
    wallet_addr = update.message.text
    if len(wallet_addr) != 42:
        update.message.reply_text("Doesn't look like wallet address. Try /crypto again.")
        return ConversationHandler.END
    if not chat_data.get('wallet'):
        chat_data['wallet'] = list()
    chat_data['wallet'].append(wallet_addr)
    save_crypto_record(update, context)
    return ConversationHandler.END


def save_crypto_record(update, context):
    logger.info('Inside Crypto record saving')
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            wallet = chat_data['wallet']
            wallet = ",,,".join(wallet)

            wallet_record: Crypto = Crypto(user_id=user.id, wallet=wallet, created_at=datetime.now())
            try:
                session.add(wallet_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving wallet to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /crypto again..")
            else:
                session.commit()
                logger.info(f"Crypto record added - {wallet_record}")
                update.effective_message.reply_text(f"Record added - \n\n"
                                                    f"{wallet_record.wallet}", parse_mode='HTML')
                update.effective_message.reply_text(f"Use /mycrypto to check previous records")
                try:
                    message_id_of_letsstart = int(chat_data['message_id_of_letsstart'])
                    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_letsstart)
                except:
                    clear_chatdata(context=context)
                    logger.exception("error converting chat_data['message_id_of_letsstart'] to int")
            clear_chatdata(context=context)


def idonthavewallet(update, context):
    update.effective_message.reply_text('No worries. Watch this 5 min video on http://cryptochimaru.com and get your own wallet with some test tokens.')
    return ConversationHandler.END


def cancelcrypto(update, context):
    update.effective_message.reply_text('Crypto command cancelled')
    return ConversationHandler.END


def timeout_crypto(update, context):
    update.effective_message.reply_text(f'Crypto command timedout! (timeout limit - {crypto_timeout_time} sec')
    return ConversationHandler.END


def mycrypto(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.crypto.count():
                for _id, item in enumerate(user.crypto.order_by('wallet').all()):
                    if _id < 5:
                        update.effective_message.reply_text(f"{_id}. {item.wallet.replace(',,,', ', ')}")
            else:
                update.effective_message.reply_text("You haven't added any wallet.\n\nUse /crypto to add wallet.\nUse /idonthavewallet to get tips.")


def mycryptorewards(update, context):
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            # update.message.reply_text("Let's start. (use /cancelthoughts if you want to cancel)")
            # chat_data = context.chat_data
            update.message.reply_text("Your rewards in RoutineBotToken will be shown here. We are working on the logic, but it'll be in relation with your number of daily logs, so keep adding logs and come back here later.")


crypto_handler = ConversationHandler(
    entry_points=[CommandHandler('crypto', crypto)],
    states={
        WALLET: [MessageHandler(Filters.text and ~Filters.command, addwallet)],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_crypto)]
    },
    fallbacks=[CommandHandler('idonthavewallet', idonthavewallet)],
    conversation_timeout=crypto_timeout_time
)