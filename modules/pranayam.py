from sqlalchemy import desc
import os
from telegram.ext import ConversationHandler, inlinequeryhandler, CallbackContext, CallbackQueryHandler, CommandHandler, \
    MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram import Update
from dbhelper import Session
import logging

from models import User, Pranayam
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

pranayam_timeout_time = 120

PRANAYAM_DATE, PRANAYAM_HOUR, PRANAYAM_MINUTE, PRANAYAM_NAME, PRANAYAM_REPETITION, PRANAYAM_NOTE = range(6)

minutes_list = [00, 10, 20, 30, 40, 50]


def generate_pranayam_keyboard():
    keyboard = [[
        InlineKeyboardButton("Dirga Pranayama", callback_data="dirga_pranayam"),
        InlineKeyboardButton("Nadi Shodhana Pranayama", callback_data="nadi_shodhana_pranayam"),
    ],
        [
            InlineKeyboardButton("Anuloma Viloma Pranayama", callback_data="anuloma_pranayam"),
            InlineKeyboardButton("Surya Bhedana Pranayama", callback_data="surya_bhedana_pranayam"),
        ],
        [
            InlineKeyboardButton("Ujjayi Pranayama", callback_data="ujjayi_pranayam"),
            InlineKeyboardButton("Bhramari Pranayama", callback_data="bhramari_pranayam"),
        ],
        [
            InlineKeyboardButton("Sitkari Pranayama", callback_data="sitkari_pranayam"),
            InlineKeyboardButton("Bhastrika Pranayama", callback_data="bhastrika_pranayam"),
        ],
        [
            InlineKeyboardButton("Kapalbhati Pranayama", callback_data="kapalbhati_pranayam"),
            InlineKeyboardButton("Simhasana Pranayama", callback_data="simhasana_pranayam"),
        ],
        [
            InlineKeyboardButton("Shitali Pranayama", callback_data="shitali_pranayam"),
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


def generate_pattern_for_pranayam_hour():
    temp = ''
    for hour in range(24):
        temp += str(hour) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def generate_pattern_for_pranayam_minute():
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


def pranayam(update, context):
    logger.info("Inside pranayam")
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.timezones.count():
                keyboard = generate_date_keyboard()
                update.message.reply_text("Let's start. (use /cancelpranayam if you want to cancel)")
                update.message.reply_text("Date of Pranayam Exercise? (Use /cancelpranayam to cancel)",
                                          reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                query_message_id = update.message.message_id + 1
                chat_data = context.chat_data
                chat_data['message_id_of_letsstart'] = query_message_id
                return PRANAYAM_DATE


def selected_pranayam_date(update: Update, context):
    logger.info("inside selected pranayam date")
    chat_data = context.chat_data
    today = datetime.today().date()
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    if query.data == 'today':
        chat_data['pranayam_date'] = today
    elif query.data == 'yday':
        chat_data['pranayam_date'] = today - timedelta(days=1)
    elif query.data == 'daybeforeyday':
        chat_data['pranayam_date'] = today - timedelta(days=2)
    elif query.data == 'other':
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /pranayam again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    else:
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /pranayam again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    hourwise_keyboard = generate_hour_keyboard()
    update.callback_query.edit_message_text("Hour of Pranayam exercise?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=hourwise_keyboard))
    return PRANAYAM_HOUR


def selected_pranayam_hour(update: Update, context):
    logger.info("inside selected pranayam exercise hour")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    hour_got = query.data.strip()
    logger.info(f'Exercise hour selected -> {hour_got}')
    keyboard = generate_minute_keyboard(hour=hour_got)
    chat_data['pranayam_hour'] = hour_got
    update.callback_query.edit_message_text("Time of Pranayam exercise?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return PRANAYAM_MINUTE


def selected_minute_for_pranayam(update: Update, context: CallbackContext):
    logger.info("inside selected pranayam minute")
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    date_selected = str(chat_data.get('pranayam_date'))
    time_selected = query.data.strip()
    chat_data['pranayam_time'] = time_selected
    pranayam_datetime = datetime.strptime(date_selected + ' ' + time_selected, '%Y-%m-%d %H:%M')
    chat_data['pranayam_datetime'] = pranayam_datetime
    logger.info(f"Selected time for Pranayam -> {pranayam_datetime}")
    keyboard = generate_pranayam_keyboard()
    update.callback_query.edit_message_text("Select type of Pranayam exercise",
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return PRANAYAM_NAME


def selected_pranayamaname(update, context):
    logger.info("Inside selected pranayam")
    query: inlinequeryhandler = update.callback_query
    chat_data = context.chat_data
    update.callback_query.answer()
    pranayam_name = query.data.strip()
    chat_data['pranayam_name'] = pranayam_name
    pranayam_type = str(chat_data.get('pranayam_name'))
    chat_data['pranayam_type'] = pranayam_type
    logger.info(f'Pranayam Exercise Type -> {pranayam_type}')
    reps_keyboard = generate_repetitions_keyboard()  # sets=sets_got
    update.callback_query.edit_message_text("Enter repetitions: ",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=reps_keyboard))
    return PRANAYAM_REPETITION


def pranayam_repetition(update, context):
    logger.info("inside selected repetitions")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    repetition = query.data.strip()
    logger.info(f'Repetition count -> {repetition}')
    chat_data['repetition'] = repetition
    update.callback_query.edit_message_text("Write notes below (else click /skip_notes)")
    return PRANAYAM_NOTE


def pranayam_notes(update, context):
    chat_data = context.chat_data
    logger.info('enter pranayam note')
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    ans = update.effective_message.text
    chat_data['pranayam_notes'] = ans
    if not chat_data.get('pranayam_notes'):
        chat_data['pranayam_notes'] = ''
    update.message.reply_text("Notes added successfully.")
    save_pranayam_record(update, context)
    return ConversationHandler.END

def skip_pranayam_notes(update, context):
    chat_data = context.chat_data
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    chat_data = context.chat_data
    if not chat_data.get('pranayam_notes'):
        chat_data['pranayam_notes'] = ''
    save_pranayam_record(update, context)
    return ConversationHandler.END


def cancelpranayam(update, context):
    update.effective_message.reply_text('Pranayam command cancelled!')
    clear_chatdata(context=context)
    return ConversationHandler.END


def save_pranayam_record(update, context):
    logger.info('Inside Pranayam record')
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            pranayam_datetime = chat_data['pranayam_datetime']
            pranayam_type = chat_data['pranayam_type']
            repetition = chat_data['repetition']
            pranayam_notes = chat_data['pranayam_notes']

            # print(user.id, pranayam_datetime, pranayam_type, repetition, pranayam_notes)
            pranayam_record: Pranayam = Pranayam(user_id=user.id, pranayam_datetime=pranayam_datetime, pranayam_type=pranayam_type,
                                     repetition=repetition, pranayam_notes=pranayam_notes, created_at=datetime.now())
            try:
                session.add(pranayam_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving pranayam to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /pranayam again..")
            else:
                session.commit()
                logger.info(f"Pranayam record added - {pranayam_record}")
                update.effective_message.reply_text(f"Record added - \n\n"
                                                    f"<b>At:</b> {readable_datetime(pranayam_record.pranayam_datetime)}\n"
                                                    f"<b>Type:</b> {pranayam_record.pranayam_type}\n"
                                                    f"<b>Reps:</b> {pranayam_record.repetition}\n"
                                                    f"<b>Notes:</b>  {pranayam_record.pranayam_notes if pranayam_record.pranayam_notes else '-'}", parse_mode='HTML')
                update.effective_message.reply_text(f"Use /mypranayam to check previous records")
                try:
                    message_id_of_letsstart = int(chat_data['message_id_of_letsstart'])
                    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_letsstart)
                except:
                    clear_chatdata(context=context)
                    logger.exception("error converting chat_data['message_id_of_letsstart'] to int")
            clear_chatdata(context=context)


def mypranayam(update: Update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.pranayams.count():
                for _id, item in enumerate(user.pranayams.order_by(desc('pranayam_datetime')).all()):
                    if _id < 5:
                        if not item.pranayam_notes:
                            update.effective_message.reply_text(f"<b>{item.pranayam_type}</b> - {item.repetition} times\n"
                                                                f"{readable_datetime(item.pranayam_datetime)}\n\n", parse_mode='HTML')
                        else:
                            update.effective_message.reply_text(f"<b>{item.pranayam_type}</b> - {item.repetition} times\n"
                                                                f"Notes - {item.pranayam_notes}\n"
                                                                f"{readable_datetime(item.pranayam_datetime)}\n\n", parse_mode='HTML')

                        # update.effective_message.reply_text(f"{readable_datetime(item.pranayam_datetime)} - {item.pranayam_type} - {item.repetition}")
            else:
                update.effective_message.reply_text("You haven't added a single Pranayam exercise record. Use /pranayam to get started")


def timeout_pranayam(update, context):
    update.effective_message.reply_text(f'Exercise command timedout! (timeout limit - {pranayam_timeout_time} sec')
    return ConversationHandler.END


def readable_datetime(inputdatetime: datetime):
    return inputdatetime.strftime('%d %b, %H:%M')


pranayam_handler = ConversationHandler(
    entry_points=[CommandHandler('pranayam', pranayam)],
    states={
        PRANAYAM_DATE: [CallbackQueryHandler(selected_pranayam_date, pattern='^today|yday|daybeforeyday|other$')],
        PRANAYAM_HOUR: [CallbackQueryHandler(selected_pranayam_hour, pattern=generate_pattern_for_pranayam_hour())],
        PRANAYAM_MINUTE: [CallbackQueryHandler(selected_minute_for_pranayam, pattern=generate_pattern_for_pranayam_minute())],
        PRANAYAM_NAME: [CallbackQueryHandler(selected_pranayamaname, pattern='^dirga_pranayam|nadi_shodhana_pranayam|anuloma_pranayam|'
                                                                     'surya_bhedana_pranayam|ujjayi|bhramari_pranayam|sitkari_pranayam|bhastrika_pranayam|'
                                                                     'kapalbhati_pranayam|simhasana_pranayam|shitali_pranayam|others$')],
        PRANAYAM_REPETITION: [CallbackQueryHandler(pranayam_repetition, pattern=generate_pattern_for_repetitions())],
        PRANAYAM_NOTE: [CommandHandler('skip_notes', skip_pranayam_notes),
                    MessageHandler(Filters.text, pranayam_notes)],

        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_pranayam)]
    },
    fallbacks=[CommandHandler('cancelpranayam', cancelpranayam)],
    conversation_timeout=pranayam_timeout_time
)