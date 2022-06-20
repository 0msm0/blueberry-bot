from telegram.ext import CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
from telegram import Update
from datetime import datetime
from models import User
from dbhelper import Session
import logging

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

NAME, EMAILID = range(2)
registration_timeout_limit=60


def register(update, context):
    """ Registration """
    chat_id = update.effective_message.chat_id
    user = check_if_user_exists(chat_id)
    if not user:
        logger.info(f"Inside /register. User not found. Going into registration flow. ")
        update.effective_message.reply_text("Let's get you registered.\nWhat's your name?")
        return NAME
    else:
        logger.info(f"Inside /register. User found. Details shown")
        # These three properties shall come from daatabase. We'll fix it, but first let's comlete the conversation flow.
        update.effective_message.reply_text(f"You are already registered with the following details\n"
                                  f"Name - {user.name}\n"
                                  f"Emaild - {user.email_id}\n")
        return ConversationHandler.END


def check_if_user_exists(chat_id):
    """ Return user from database (returns None implicitly if not found) """
    with Session() as session:
        user = User.get_user_by_chatid(session=session, chat_id=chat_id)
        return user


def name(update, context):
    msg = update.effective_message.text.strip()
    if len(msg) > 30:
        update.effective_message.reply_text('Too long a name. Try shorter one.')
        logger.info(f"Inside /register. Got very very long name > 30 - {msg}")
        return NAME
    if len(msg) < 2:
        update.effective_message.reply_text('Too short a name. Try longer one.')
        logger.info(f"Inside /register. Got very very short name < 2 - {msg}")
        return NAME
    update.effective_message.reply_text(f"Nice to know you, {msg}\nNow your email id - ")
    user_data = context.user_data
    user_data['name'] = msg
    user_data['chat_id'] = update.effective_message.chat_id
    logger.info(f"Inside /register. Got name - {user_data['name']}")
    # We are storing this user data in the storage provided by TG, and at once we'll store it in db'
    return EMAILID


def check_if_email_already_exists(email_id):
    with Session() as sess:
        res = sess.query(User).filter(User.email_id == email_id).first()
        return res


def wrong_email(update, context):
    logger.info(f"Inside /register. Got wrong email id.")
    update.effective_message.reply_text("Wrong email. Try again")
    return EMAILID


def email(update, context):
    email_id = update.effective_message.text.strip()
    old_email_flag = check_if_email_already_exists(email_id)
    if old_email_flag:
        update.effective_message.reply_text(f"Email already in use.\nUse another one.")
        logger.info(f"/register - email --> ALREADY EXIST: {email_id}")
        return EMAILID
    user_data = context.user_data
    user_data['email_id'] = email_id
    # update.effective_message.reply_text("That's it..")
    logger.info(f"Inside /register. Got email - {user_data['email_id']}")
    save_user(update, context)  # UNIQUE EMAIL ID CASE IS REMAINED
    update.effective_message.reply_text("/set_timezone now so we can store logs in your local time")
    return ConversationHandler.END


def timeout_register(update, context):
    update.effective_message.reply_text(f'Timeout. Kindly /register again. (Timeout limit - {registration_timeout_limit} sec)')
    logger.info(f"Timeout for /addlog")
    clear_userdata(context=context)
    logger.info(f"context.user_data cleared")


def save_user(update:Update, context: CallbackContext):
    user_data = context.user_data
    name = user_data['name']
    email_id = user_data['email_id']
    # phone_no = user_data['phone_no']
    chat_id = user_data['chat_id']
    tg_username = update.effective_message.from_user.username
    # created_at = datetime.datetime.now()
    user = User(chat_id=chat_id,tg_username=tg_username, name=name, email_id=email_id, created_at=datetime.now(), updated_at=datetime.now())

    with Session() as session:
        try:
            session.add(user)
        except:
            session.rollback()
            clear_userdata(context=context)
            logger.error(f"Some error saving user while registering!", exc_info=True)
            update.effective_message.reply_text("Something wrong. Please try later or contact admin..")
        else:
            session.commit()
            logger.info(f"User created - {user}")
            clear_userdata(context=context)
            update.effective_message.reply_text(f"Awesome, you got registered with the following details\n"
                                      f"<b>Name</b> - {user.name}\n"
                                      f"<b>Email</b> - {user.email_id}\n", parse_mode='HTML')


def reg_cancel(update, context):
    logger.info(f"Inside /reg_cancel. Some error.")
    update.effective_message.reply_text('Registration cancelled!')
    clear_userdata(context=context)
    return ConversationHandler.END


def clear_userdata(context):
    context.user_data.clear()
    logger.info(f"user_data cleared")


def clear_chatdata(context):
    context.chat_data.clear()
    logger.info(f"chat_data cleared")

registration_handler = ConversationHandler(
    entry_points=[CommandHandler('register', register)],
    states={
        NAME: [MessageHandler(Filters.text, name)],
        EMAILID: [MessageHandler(Filters.regex(r'^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$'), email),
                  MessageHandler(~Filters.regex(r'^([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$'), wrong_email)],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout_register)]
    },
    fallbacks=[CommandHandler('reg_cancel', reg_cancel)],
    conversation_timeout=registration_timeout_limit
)
