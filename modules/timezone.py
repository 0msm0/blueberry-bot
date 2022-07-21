from sqlalchemy import desc
from telegram.ext import CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, inlinequeryhandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta
from models import User, Timezone
from dbhelper import Session
import logging
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_userdata
# TODO - DONT ALLOW USER TO SET THE SAME TIMEZONE AGAIN. ie. set_timezone needs to be used only if ZONE IS TO BE CHANGED.


log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

set_timezone_timeout = 30
TZCOUNTRY, TZNAME, TZEFFECTIVEFROM = range(3)
uk_list = ['uk', 'united kingdom', 'great britain', 'britain']
us_list = ['us', 'united states', 'united states of america', 'america']

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
                update.effective_message.reply_text("Cool, you are all set! Use /wakesleep /food to get started!\nUse / to populate list of commands.")
                clear_userdata(context=context)


def mytimezone(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.timezones.count():
                for _id, item in enumerate(user.timezones.order_by(desc('created_at')).all()):
                    update.effective_message.reply_text(f"Timezone <b>{item.timezone_name}</b> set since <b>{item.effective_from}</b>", parse_mode='HTML')
                # nl = '\n'
                # update.effective_message.reply_text([(item.timezone_name, str(item.effective_from)) for item in user.timezones.all()])
            else:
                update.effective_message.reply_text("You haven't added any timezone. You need to /set_timezone before you start logging.")


def timeout_timezone(update, context):
    update.effective_message.reply_text(f'Set Timezone command timed out!')
    logger.info("Setting timezone timed out")
    return ConversationHandler.END

def cancel_timezone(update, context):
    update.effective_message.reply_text(f'Set Timezone command cancelled!')
    logger.info("Setting timezone cancelled")
    return ConversationHandler.END


# if __name__ == '__main__':
set_timezone_handler = ConversationHandler(
    entry_points=[CommandHandler('set_timezone', set_timezone)],
    states={
        TZCOUNTRY: [MessageHandler(Filters.text, tzcountry)],
        TZNAME: [CallbackQueryHandler(tzname, pattern='^' + '|'.join(ALL_TZ_NAMES) + '$')],
        TZEFFECTIVEFROM: [CallbackQueryHandler(tzeffectivefrom, pattern='^sincefirstday|yesterday|today$')],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_timezone)]
    },
    fallbacks=[CommandHandler('cancel_timezone', cancel_timezone)],
    conversation_timeout=set_timezone_timeout
)
