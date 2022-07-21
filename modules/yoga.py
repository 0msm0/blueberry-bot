from sqlalchemy import desc
import os
from telegram.ext import ConversationHandler, inlinequeryhandler, CallbackContext, CallbackQueryHandler, CommandHandler, \
    MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram import Update
from dbhelper import Session
import logging

from models import User, Yoga
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chatdata
from datetime import datetime, timedelta
import requests

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

yoga_timeout_time = 120

YOGA_DATE, YOGA_HOUR, YOGA_MINUTE, YOGA_NAME, YOGA_REPETITION, YOGA_NOTE = range(6)


minutes_list = [00, 10, 20, 30, 40, 50]


def generate_yoga_keyboard():
    keyboard = [[
            InlineKeyboardButton("Surya Namaskar", callback_data="surya_namaskar"),
        ],
        [
            InlineKeyboardButton("Adho Mukha Svansana", callback_data="adho_mukha_svanasana"),
            InlineKeyboardButton("Chakarasana", callback_data="chakarasana"),
        ],
        [
            InlineKeyboardButton("Sukhasana", callback_data="sukhasana"),
            InlineKeyboardButton("Ardha Chandrasana", callback_data="ardha_chandrasana"),
        ],
        [
            InlineKeyboardButton("Garudasana", callback_data="garudasana"),
            InlineKeyboardButton("Shavasana", callback_data="shavasana"),
        ],
        [
            InlineKeyboardButton("Balasana", callback_data="balasana"),
            InlineKeyboardButton("Vajrasana", callback_data="vajrasana"),
        ],
        [
            InlineKeyboardButton("Bhujangasana", callback_data="bhujangasana"),
            InlineKeyboardButton("Shirshasana", callback_data="shirshasana"),
        ],
        [
            InlineKeyboardButton("Gomukhasana", callback_data="gomukhasana"),
            InlineKeyboardButton("Others", callback_data="others"),
        ]]
    return keyboard


def generate_date_keyboard():
    keyboard = [[
        InlineKeyboardButton("today", callback_data="today"),
        InlineKeyboardButton("yday", callback_data="yday"),
        InlineKeyboardButton("daybeforeyday", callback_data="daybeforeyday"),
        InlineKeyboardButton("other", callback_data="other"),  # TODO - Handle this
    ]]
    return keyboard


def generate_hour_keyboard():
    super_keys = []
    keys = []
    rowlimit = 4
    no_of_keys_in_row = 0

    for hour in range(24):
        key = InlineKeyboardButton(f"{hour}-{hour + 1}", callback_data=str(hour))
        if no_of_keys_in_row == rowlimit:
            super_keys.append(keys.copy())  # [[01,12,23,34]]
            keys.clear()
            no_of_keys_in_row = 0
        keys.append(key)  # 0-1, 1-2, 2-3, 3-4  # 4-5
        no_of_keys_in_row += 1  # 1,2, 3, 4, 1
    super_keys.append(keys.copy())
    return super_keys


def generate_minute_keyboard(hour):
    minutes_to_show = [str(hour) + ':' + str(round(minute, 2)) for minute in
                       minutes_list]  # TODO - should show 9:00 instead of 9:0
    keys = []
    for item in minutes_to_show:
        key = InlineKeyboardButton(f"{item}", callback_data=str(item))
        keys.append(key)
    final_minutes_keyboard = [keys]
    return final_minutes_keyboard


def generate_repetitions_keyboard():
    super_keys = []
    keys = []
    rowlimit = 5
    no_of_keys_in_row = 0
    for repetition in range(1,16):
        key = InlineKeyboardButton(f"{repetition}", callback_data=str(repetition))
        if no_of_keys_in_row == rowlimit:
            super_keys.append(keys.copy())
            keys.clear()
            no_of_keys_in_row = 0
        keys.append(key)
        no_of_keys_in_row += 1
    super_keys.append(keys.copy())
    return super_keys


def generate_pattern_for_yoga_hour():
    temp = ''
    for hour in range(24):
        temp += str(hour) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def generate_pattern_for_yoga_minute():
    temp = ''
    for hour in range(24):
        for minute in minutes_list:
            temp += str(hour) + ':' + str(minute) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def generate_pattern_for_repetitions():
    temp = ''
    for repetition in range(1,16):
        temp += str(repetition) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern

def yoga(update, context):
    logger.info("Inside yoga")
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.timezones.count():
                keyboard = generate_date_keyboard()
                update.message.reply_text("Let's start. (use /cancelyoga if you want to cancel)")
                update.message.reply_text("Date of Yoga Exercise?",
                                          reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                query_message_id = update.message.message_id + 1
                chat_data = context.chat_data
                chat_data['message_id_of_letsstart'] = query_message_id
                return YOGA_DATE


def selected_yoga_date(update: Update, context):
    logger.info("inside selected yoga date")
    chat_data = context.chat_data
    today = datetime.today().date()
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    if query.data == 'today':
        chat_data['yoga_date'] = today
    elif query.data == 'yday':
        chat_data['yoga_date'] = today - timedelta(days=1)
    elif query.data == 'daybeforeyday':
        chat_data['yoga_date'] = today - timedelta(days=2)
    elif query.data == 'other':
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /yoga again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    else:
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /yoga again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    hourwise_keyboard = generate_hour_keyboard()
    update.callback_query.edit_message_text("Hour of Yoga exercise?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=hourwise_keyboard))
    return YOGA_HOUR

def selected_yoga_hour(update: Update, context):
    logger.info("inside selected yoga exercise hour")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    hour_got = query.data.strip()
    logger.info(f'Yoga hour selected -> {hour_got}')
    keyboard = generate_minute_keyboard(hour=hour_got)
    chat_data['yoga_hour'] = hour_got
    update.callback_query.edit_message_text("Time of Yoga exercise?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return YOGA_MINUTE

def selected_minute_for_yoga(update: Update, context: CallbackContext):
    logger.info("inside selected yoga minute")
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    date_selected = str(chat_data.get('yoga_date'))
    time_selected = query.data.strip()
    chat_data['yoga_time'] = time_selected
    yoga_datetime = datetime.strptime(date_selected + ' ' + time_selected, '%Y-%m-%d %H:%M')
    chat_data['yoga_datetime'] = yoga_datetime
    logger.info(f"Selected time for Yoga -> {yoga_datetime}")
    keyboard = generate_yoga_keyboard()
    update.callback_query.edit_message_text("Select type of Yoga exercise",
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return YOGA_NAME

def selected_yoganame(update, context):
    logger.info("Inside selected yoga")
    query: inlinequeryhandler = update.callback_query
    chat_data = context.chat_data
    update.callback_query.answer()
    yoga_name = query.data.strip()
    chat_data['yoga_name'] = yoga_name
    yoga_type = str(chat_data.get('yoga_name'))
    chat_data['yoga_type'] = yoga_type
    logger.info(f'Yoga Exercise Type -> {yoga_type}')
    reps_keyboard = generate_repetitions_keyboard()  # sets=sets_got
    update.callback_query.edit_message_text("Enter repetitions: ",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=reps_keyboard))
    return YOGA_REPETITION

def yoga_repetition(update, context):
    logger.info("inside selected repetitions")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    repetition = query.data.strip()
    logger.info(f'Repetition count -> {repetition}')
    chat_data['repetition'] = repetition
    update.callback_query.edit_message_text("Write notes below (else click /skip_notes)")
    return YOGA_NOTE

def yoga_notes(update, context):
    chat_data = context.chat_data
    logger.info('enter yoga note')
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    ans = update.effective_message.text
    chat_data['yoga_notes'] = ans
    if not chat_data.get('yoga_notes'):
        chat_data['yoga_notes'] = ''
    update.message.reply_text("Notes added successfully.")
    save_yoga_record(update, context)
    return ConversationHandler.END


def skip_yoga_notes(update, context):
    chat_data = context.chat_data
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    chat_data = context.chat_data
    if not chat_data.get('yoga_notes'):
        chat_data['yoga_notes'] = ''
    save_yoga_record(update, context)
    return ConversationHandler.END


def cancelyoga(update, context):
    update.effective_message.reply_text('Yoga command cancelled!')
    clear_chatdata(context=context)
    return ConversationHandler.END

def save_yoga_record(update, context):
    logger.info('Inside Yoga record')
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            yoga_datetime = chat_data['yoga_datetime']
            yoga_type = chat_data['yoga_type']
            repetition = chat_data['repetition']
            yoga_notes = chat_data['yoga_notes']

            # print(user.id, yoga_datetime, yoga_type, repetition, yoga_notes)
            yoga_record: Yoga = Yoga(user_id=user.id, yoga_datetime=yoga_datetime, yoga_type=yoga_type,
                                     repetition=repetition, yoga_notes=yoga_notes, created_at=datetime.now())
            try:
                session.add(yoga_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving yoga to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /yoga again..")
            else:
                session.commit()
                logger.info(f"Yoga record added - {yoga_record}")
                update.effective_message.reply_text(f"Record added - \n\n"
                                                    f"<b>At:</b> {readable_datetime(yoga_record.yoga_datetime)}\n"
                                                    f"<b>Name:</b> {yoga_record.yoga_type}\n"
                                                    f"<b>Reps:</b> {yoga_record.repetition}\n"
                                                    f"<b>Notes:</b>  {yoga_record.yoga_notes if yoga_record.yoga_notes else '-'}", parse_mode='HTML')
                try:
                    message_id_of_letsstart = int(chat_data['message_id_of_letsstart'])
                    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_letsstart)
                except:
                    clear_chatdata(context=context)
                    logger.exception("error converting chat_data['message_id_of_letsstart'] to int")
            clear_chatdata(context=context)


def myyoga(update: Update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.yogas.count():
                for _id, item in enumerate(user.yogas.order_by(desc('yoga_datetime')).all()):
                    if _id < 5:
                        if not item.yoga_notes:
                            update.effective_message.reply_text(f"<b>{item.yoga_type}</b> - {item.repetition} times\n"
                                                                f"{readable_datetime(item.yoga_datetime)}\n\n", parse_mode='HTML')
                        else:
                            update.effective_message.reply_text(f"<b>{item.yoga_type}</b> - {item.repetition} times\n"
                                                                f"Notes - {item.yoga_notes}\n"
                                                                f"{readable_datetime(item.yoga_datetime)}\n\n", parse_mode='HTML')
            else:
                update.effective_message.reply_text("You haven't added a single Yoga exercise record. Use /yoga to get started")

def timeout_yoga(update, context):
    update.effective_message.reply_text(f'Yoga command timedout! (timeout limit - {yoga_timeout_time} sec')
    return ConversationHandler.END


def readable_datetime(inputdatetime: datetime):
    return inputdatetime.strftime('%d %b, %H:%M')


yoga_handler = ConversationHandler(
    entry_points=[CommandHandler('yoga', yoga)],
    states={
        YOGA_DATE: [CallbackQueryHandler(selected_yoga_date, pattern='^today|yday|daybeforeyday|other$')],
        YOGA_HOUR: [CallbackQueryHandler(selected_yoga_hour, pattern=generate_pattern_for_yoga_hour())],
        YOGA_MINUTE: [CallbackQueryHandler(selected_minute_for_yoga, pattern=generate_pattern_for_yoga_minute())],
        YOGA_NAME: [CallbackQueryHandler(selected_yoganame, pattern='^surya_namaskar|adho_mukha_svanasana|chakarasana|sukhasana|'
                                                                    'ardha_chandrasana|garudasana|shavasana|balasana|vajrasana|'
                                                                    'bhujangasana|shirshasana|gomukhasana|others$')],
        YOGA_REPETITION: [CallbackQueryHandler(yoga_repetition, pattern=generate_pattern_for_repetitions())],
        YOGA_NOTE: [CommandHandler('skip_notes', skip_yoga_notes),
                    MessageHandler(Filters.text, yoga_notes)],

        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_yoga)]
    },
    fallbacks=[CommandHandler('cancelyoga', cancelyoga)],
    conversation_timeout=yoga_timeout_time
)
