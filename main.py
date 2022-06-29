from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, inlinequeryhandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from constants import *
from models import User, Timezone, Wakesleep, Food
from dbhelper import Session, engine
import logging
load_dotenv()
from modules.registration import registration_handler
from modules.timezone import set_timezone_handler, mytimezones
from modules.wakesleep import wakesleep_handler, mywakesleeps
from modules.getcurrentuser import get_current_user
from modules.food import food, food_handler, donephotos


log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

token = os.environ.get('bot_token')

# wakeup_timeout_time = 60
# registration_timeout_limit=60
# set_timezone_timeout = 30
# wakeuphour_timeout_time = 20
# WAKEUPHOUR, WAKEUPMINUTE, WAKEUP_COMMENT = range(3)
# NAME, EMAILID = range(2)
# TZCOUNTRY, TZNAME, TZEFFECTIVEFROM = range(3)
END = ConversationHandler.END
# uk_list = ['uk', 'united kingdom', 'great britain', 'britain']
# us_list = ['us', 'united states', 'united states of america', 'america']


def start(update: Update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        # update.effective_message.reply_text("What's your timezone?")
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            update.effective_message.reply_text(f"Hey, {user.name}.\n"
                                      f"Try /wakesleep /mywakesleeps /food to start adding your logs.")
'''
def get_current_user(chat_id, update, context: CallbackContext, session):
    """ Get current user from context, returns instance of User class. If not, send std message to user """
    user_data = context.user_data
    user = User.get_user_by_chatid(session=session, chat_id=chat_id)
    if user:
        user_data['user'] = user  # TODO REMOVE IF REMAINS UNUSED AT THE END OF THE PROJECT
        logger.info(f"Got user from db and stored to user_data - {user_data['user']} for FUTURE USE if any")
        return user
    else:
        logger.info(f"User not found. Sent message to register")
        update.effective_message.reply_text(f"Hey, you need to /register first")
        return None
'''
'''
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
            update.effective_message.reply_text("You can start adding your logs with /wakeup")


def reg_cancel(update, context):
    logger.info(f"Inside /reg_cancel. Some error.")
    update.effective_message.reply_text('Registration cancelled!')
    clear_userdata(context=context)
    return ConversationHandler.END
'''
'''
def clear_userdata(context):
    context.user_data.clear()
    logger.info(f"user_data cleared")


def clear_chatdata(context):
    context.chat_data.clear()
    logger.info(f"chat_data cleared")
'''
'''
def wakeup(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.timezones.count():
                keyboard = [[
                    InlineKeyboardButton("3-4am",callback_data="threetofouram"),
                    InlineKeyboardButton("4-5am",callback_data="fourtofiveam"),
                ]]
                update.effective_message.reply_text("Select hour. (/cancel_wakeup to cancel)", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                return WAKEUPHOUR
            else:
                update.effective_message.reply_text("You need to /set_timezone first")
                return ConversationHandler.END


def selected_wakeup_hour(update: Update, context):
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    if query.data=='threetofouram':
        three_four_keyboard = [[
            InlineKeyboardButton("3.10am", callback_data=str(threetenam)),
            InlineKeyboardButton("3.20am", callback_data=str(threetwentyam)),
        ]]
        update.callback_query.edit_message_text("Now enter time", reply_markup=InlineKeyboardMarkup(inline_keyboard=three_four_keyboard))
    elif query.data=='fourtofiveam':
        four_five_keyboard = [[
            InlineKeyboardButton("4.10am", callback_data=str(fourtenam)),
            InlineKeyboardButton("4.20am", callback_data=str(fourtwentyam)),
        ]]
        update.callback_query.edit_message_text("Now enter time", reply_markup=InlineKeyboardMarkup(inline_keyboard=four_five_keyboard))
    return WAKEUPMINUTE


#TODO Handle '3.10am' list strings in constant
def selected_wakeup_minute(update: Update, context):
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    wakeup_time = ''
    if query.data=='threetenam':
        wakeup_time = '3.10am'
    elif query.data=='threetwentyam':
        wakeup_time = '3.20am'
    elif query.data=='fourtenam':
        wakeup_time = '4.10am'
    elif query.data=='fourtwentyam':
        wakeup_time = '4.20am'
    chat_data['wakeup_time'] = wakeup_time

    update.callback_query.message.reply_text("Add comment? (Use /skip_wakeup_comment to cancel)")
    return WAKEUP_COMMENT


def wakeup_comment(update, context):
    chat_data = context.chat_data
    ans = update.effective_message.text
    chat_data['wakeup_comment'] = ans
    if not chat_data.get('wakeup_comment'):
        chat_data['wakeup_comment'] = ''
    update.effective_message.reply_text(f"Your record\n"
                              f"<b>Wakeup time</b> -> {chat_data['wakeup_time']}\n"
                              f"<b>Comment</b> -> {chat_data['wakeup_comment']}", parse_mode='HTML')
    clear_chatdata(context)
    return ConversationHandler.END

def cancel_wakeup(update, context):
    update.effective_message.reply_text(f'Wakeup command cancelled!')
    return ConversationHandler.END

def cancel_wakeup_hour(update, context):
    update.effective_message.reply_text(f'Wakeup hour NESTED command cancelled!')
    return ConversationHandler.END

def cancel_wakeup_comment(update, context):
    update.effective_message.reply_text(f'Wakeup comment cancelled!')
    return ConversationHandler.END

def skip_wakeup_comment(update, context):
    chat_data = context.chat_data
    if not chat_data.get('wakeup_comment'):
        chat_data['wakeup_comment'] = ''
    update.effective_message.reply_text(f"Your record\n"
                              f"<b>Wakeup time</b> -> {chat_data['wakeup_time']}\n"
                              f"<b>Comment</b> -> None", parse_mode='HTML')
    clear_chatdata(context)  # DO THIS AFTER SAVING DATA TO DB
    return ConversationHandler.END
'''
'''
def set_timezone(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            update.effective_message.reply_text('Which country do you live in?')
            return TZCOUNTRY


def tzcountry(update, context):
    user_country = update.effective_message.text.strip()
    user_data = context.user_data
    user_data['tzcountry'] = user_country
    #TODO - IMPROVE THIS LOGIC SOMETIME
    keyboard = [[]]
    if user_country.lower() == 'india':
        keyboard = [[
            InlineKeyboardButton("Asia/Kolkata", callback_data="Asia/Kolkata"),
        ]]
    elif user_country.lower() in uk_list:
        keyboard = [[
            InlineKeyboardButton("Europe/London", callback_data="Europe/London"),
        ]]
    elif user_country.lower() in us_list:
        keyboard = [[
            InlineKeyboardButton("Pacific/Honolulu", callback_data="Pacific/Honolulu"),
            InlineKeyboardButton("America/Anchorage", callback_data="America/Anchorage"),
            InlineKeyboardButton("America/Los_Angeles", callback_data="America/Los_Angeles"),
            InlineKeyboardButton("America/Denver", callback_data="America/Denver"),
            InlineKeyboardButton("America/Chicago", callback_data="America/Chicago"),
            InlineKeyboardButton("America/New_York", callback_data="America/New_York"),
        ]]
    else:
        update.effective_message.reply_text('Currently, the beta supports only India US UK.\nSet your country as India for now, you can change it later.\nSimply write India below..')
        return TZCOUNTRY
    update.effective_message.reply_text("Select timezone", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return TZNAME


ALL_TZ_NAMES = ['Asia/Kolkata', 'Europe/London', 'Pacific/Honolulu','America/Anchorage','America/Los_Angeles','America/Denver','America/Chicago','America/New_York',]
def tzname(update:Update, context):
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    user_data = context.user_data

    if query.data == 'Asia/Kolkata':
        user_data['tzcountry'] = 'India'
        user_data['tzname'] = 'Asia/Kolkata'
        user_data['tzoffset'] = '+5:30'
    elif query.data == 'Europe/London':
        user_data['tzcountry'] = 'UK'
        user_data['tzname'] = 'Europe/London'
        user_data['tzoffset'] = '+1:00'
    elif query.data == 'Pacific/Honolulu':
        user_data['tzcountry'] = 'US'
        user_data['tzname'] = 'Pacific/Honolulu'
        user_data['tzoffset'] = '-10:00'
    elif query.data == 'America/Anchorage':
        user_data['tzcountry'] = 'US'
        user_data['tzname'] = 'America/Anchorage'
        user_data['tzoffset'] = '-9:00'
    elif query.data == 'America/Los_Angeles':
        user_data['tzcountry'] = 'US'
        user_data['tzname'] = 'America/Los_Angeles'
        user_data['tzoffset'] = '-8:00'
    elif query.data == 'America/Denver':
        user_data['tzcountry'] = 'US'
        user_data['tzname'] = 'America/Denver'
        user_data['tzoffset'] = '-7:00'
    elif query.data == 'America/Chicago':
        user_data['tzcountry'] = 'US'
        user_data['tzname'] = 'America/Chicago'
        user_data['tzoffset'] = '-6:00'
    elif query.data == 'America/New_York':
        user_data['tzcountry'] = 'US'
        user_data['tzname'] = 'America/New_York'
        user_data['tzoffset'] = '-5:00'
    keyboard = [[
            InlineKeyboardButton("Since First Day", callback_data='sincefirstday'),
            InlineKeyboardButton("Yesterday", callback_data='yesterday'),
            InlineKeyboardButton("Today", callback_data='today'),
        ]]
    update.callback_query.edit_message_text("Since when do you want to set this timezone", reply_markup=InlineKeyboardMarkup(keyboard))
    return TZEFFECTIVEFROM


def tzeffectivefrom(update, context):
    query = update.callback_query
    update.callback_query.answer()
    user_data = context.user_data
    if query.data == 'sincefirstday':
        user_data['tzeffectivefrom'] = 'sincefirstday'
    elif query.data == 'yesterday':
        user_data['tzeffectivefrom'] = 'yesterday'
    elif query.data == 'today':
        user_data['tzeffectivefrom'] = 'today'
    save_timezone_records(update, context)
    return ConversationHandler.END


def save_timezone_records(update:Update, context: CallbackContext):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            user_data = context.user_data
            today = datetime.today().date()
            try:
                if user_data['tzeffectivefrom'] == 'sincefirstday':
                    tzeffectivefrom_date = user.created_at.date()
                elif user_data['tzeffectivefrom'] == 'yesterday':
                    tzeffectivefrom_date = today - timedelta(days=1)
                elif user_data['tzeffectivefrom'] == 'today':
                    tzeffectivefrom_date = today
                else:
                    tzeffectivefrom_date = user.created_at.date()
            except:
                tzeffectivefrom_date = user.created_at.date()
                pass
            mytimezone = Timezone(user_id=user.id, timezone_name=user_data['tzname'], timezone_offset=user_data['tzoffset'],
                            effective_from=tzeffectivefrom_date, created_at=datetime.now())
            try:
                session.add(mytimezone)
            except:
                session.rollback()
                clear_userdata(context=context)
                logger.error(f"Error saving timezone", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /set_timezone again..")
            else:
                session.commit()
                logger.info(f"Timezone record added - {mytimezone}")
                update.effective_message.reply_text(f"Awesome, your timezone is all set -> \n\n"
                                          f"Tz name: {mytimezone.timezone_name}\n"
                                          f"Tz offset: {mytimezone.timezone_offset}\n"
                                          f"Tz effective from:  {mytimezone.effective_from}")
                clear_userdata(context=context)




def mytimezones(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        print(user.timezones.all())
        if user:
            if user.timezones.count():
                # nl = '\n'
                update.effective_message.reply_text([(item.timezone_name, str(item.effective_from)) for item in user.timezones.all()])
            else:
                update.effective_message.reply_text("You haven't any timezone. You need to /set_timezone before you start logging.")


def timeout_timezone(update, context):
    update.effective_message.reply_text(f'Set Timezone command timed out!')
    logger.info("Setting timezone timed out")
    return ConversationHandler.END

def cancel_timezone(update, context):
    update.effective_message.reply_text(f'Set Timezone command cancelled!')
    logger.info("Setting timezone cancelled")
    return ConversationHandler.END
'''


def error_callback(update, context):
    try:
        logger.error(f"ERROR from error_callback. Update - {update} caused error {context.error}", exc_info=True)
    except:
        logger.error(f"EXCEPTION from error_callback. Update - {update} caused error {context.error}", exc_info=True)


if __name__ == '__main__':

    # print(range(24))
    # today_date = datetime.today().date()
    # time = '3.10am'
    # final = str(today_date) + " " + time
    # print(final)
    # converted = datetime.strptime(final, '%Y-%m-%d %H.%M%p')
    # print(converted)
    # print(type(converted))
    # print(converted.astimezone())


    User.__table__.create(engine, checkfirst=True)
    Timezone.__table__.create(engine, checkfirst=True)
    Wakesleep.__table__.create(engine, checkfirst=True)
    Food.__table__.create(engine, checkfirst=True)
    updater = Updater(token=token, use_context=True)
    dp: Dispatcher = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('mytimezones', mytimezones))
    dp.add_handler(CommandHandler('mywakesleeps', mywakesleeps))
   
    # dp.add_handler(MessageHandler(Filters.text, test))
    # dp.add_handler(CommandHandler('wakeup', wakeup))
    # dp.add_handler(CommandHandler('sleep', sleep))


    '''
    
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

    '''

    '''
    wakeup_conv = ConversationHandler(
        entry_points=[CommandHandler('wakeup', wakeup)],
        states={
                # WAKEUPHOUR: [wakeuphour_conv],
                WAKEUPHOUR: [CallbackQueryHandler(selected_wakeup_hour, pattern='^'+str(threetofouram) + '|' + str(fourtofiveam) + '$')],
                WAKEUPMINUTE: [CallbackQueryHandler(selected_wakeup_minute,
                                                    pattern='^' +str(threetenam)+ '|' +str(threetwentyam)+ '|' +str(fourtenam)+ '|' +str(fourtwentyam)+'$')],
                WAKEUP_COMMENT: [MessageHandler(Filters.regex('skip_wakeup_comment'), skip_wakeup_comment),
                                MessageHandler(Filters.text, wakeup_comment)],
                ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, cancel_wakeup)]
        },
        fallbacks=[CommandHandler('cancel_wakeup', cancel_wakeup)],
        conversation_timeout=wakeup_timeout_time
    )
    '''

    '''
    set_timezone_conv = ConversationHandler(
        entry_points=[CommandHandler('set_timezone', set_timezone)],
        states={
            TZCOUNTRY:[MessageHandler(Filters.text, tzcountry)],
            TZNAME:[CallbackQueryHandler(tzname, pattern='^'+ '|'.join(ALL_TZ_NAMES) +'$')],
            TZEFFECTIVEFROM:[CallbackQueryHandler(tzeffectivefrom, pattern='^sincefirstday|yesterday|today$')],
            ConversationHandler.TIMEOUT:[MessageHandler(Filters.text and ~Filters.command, timeout_timezone)]
        },
        fallbacks=[CommandHandler('cancel_timezone',cancel_timezone)],
        conversation_timeout=set_timezone_timeout
    )
    '''

    dp.add_handler(registration_handler)
    dp.add_handler(set_timezone_handler)
    dp.add_handler(wakesleep_handler)
    dp.add_handler(food_handler)
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