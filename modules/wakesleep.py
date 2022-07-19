from sqlalchemy import desc
from telegram.ext import ConversationHandler, inlinequeryhandler, CallbackContext, CallbackQueryHandler, CommandHandler, \
    MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from dbhelper import Session
import logging
from models import User, Wakesleep
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chatdata
from datetime import datetime, timedelta

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)
logger.setLevel('INFO')
file_handler = logging.FileHandler("logs/app.log")
formatter = logging.Formatter(log_format)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

wakesleep_timeout_time = 60
SLEEPDATE, SLEEPHOUR, SLEEPMINUTE, WAKEUPDATE, WAKEUPHOUR, WAKEUPMINUTE, WAKEUP_NOTE = range(7)
minutes_list = [00, 10, 20, 30, 40, 50]


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
        key = InlineKeyboardButton(f"{hour}-{hour+1}", callback_data=str(hour))
        if no_of_keys_in_row == rowlimit:
            super_keys.append(keys.copy())  # [[01,12,23,34]]
            keys.clear()
            no_of_keys_in_row = 0
        keys.append(key)  # 0-1, 1-2, 2-3, 3-4  # 4-5
        no_of_keys_in_row += 1 # 1,2, 3, 4, 1
    super_keys.append(keys.copy())
    return super_keys


def generate_minute_keyboard(hour):
    minutes_to_show = [str(hour) + ':' + str(round(minute, 2)) for minute in minutes_list]  # TODO - should show 9:00 instead of 9:0
    keys = []
    for item in minutes_to_show:
        key = InlineKeyboardButton(f"{item}", callback_data=str(item))
        keys.append(key)
    final_minutes_keyboard = [keys]
    return final_minutes_keyboard


def generate_pattern_for_wakesleep_hour():
    temp = ''
    for hour in range(24):
        temp += str(hour) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def generate_pattern_for_wakesleep_minute():
    temp = ''
    for hour in range(24):
        for minute in minutes_list:
            temp += str(hour) + ':' + str(minute) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def wakesleep(update, context):
    logger.info("Inside wakeup")
    with Session() as session:
        chat_id = update.message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.timezones.count():
                keyboard = generate_date_keyboard()
                update.message.reply_text("Adding sleep, wakeup details..\n(use /cancel_wakesleep to cancel)")
                update.message.reply_text("Date of sleep?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                return SLEEPDATE
            else:
                update.message.reply_text("You need to /set_timezone first")
                return ConversationHandler.END


def selected_sleep_date(update: Update, context):
    chat_data = context.chat_data
    today = datetime.today().date()
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    if query.data == 'today':
        chat_data['sleep_date'] = today
    elif query.data == 'yday':
        chat_data['sleep_date'] = today - timedelta(days=1)
    elif query.data == 'daybeforeyday':
        chat_data['sleep_date'] = today - timedelta(days=2)
    elif query.data == 'other':
        update.effective_message.reply_text("This function is yet to be handled.\n Use /wakesleep again to enter recent logs.") #TODO - handle this
        return ConversationHandler.END
    else:
        update.effective_message.reply_text("This function is yet to be handled.\n Use /wakesleep again to enter recent logs.") #TODO - handle this
        return ConversationHandler.END
    hourwise_keyboard = generate_hour_keyboard()
    update.callback_query.edit_message_text("Hour of sleep?", reply_markup=InlineKeyboardMarkup(inline_keyboard=hourwise_keyboard))
    return SLEEPHOUR


def selected_sleep_hour(update: Update, context):
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    hour_got = query.data.strip()
    logger.info(f'Sleep hour selected -> {hour_got}')
    keyboard = generate_minute_keyboard(hour=hour_got)
    chat_data['sleep_hour'] = hour_got
    update.callback_query.edit_message_text("Time of sleep?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return SLEEPMINUTE


def readable_datetime(inputdatetime: datetime):
    return inputdatetime.strftime('%d %b, %H:%M')


def selected_sleep_minute(update: Update, context: CallbackContext):
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    date_selected = str(chat_data.get('sleep_date'))
    time_selected = query.data.strip()
    chat_data['raw_sleep_time'] = time_selected
    final_sleep_datetime = datetime.strptime(date_selected + ' ' + time_selected, '%Y-%m-%d %H:%M')
    chat_data['final_sleep_time'] = final_sleep_datetime
    logger.info(f"Final selected time for Sleep -> {final_sleep_datetime}")
    query_message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id = query_message_id)
    # update.callback_query.delete_message(chat_id=update.effective_message.chat_id, hamessage_id=query_message_id)
    context.bot.send_message(chat_id=update.effective_message.chat_id,
                             text=f"Slept at: {readable_datetime(final_sleep_datetime)}")

    keyboard = generate_date_keyboard()
    context.bot.send_message(chat_id=update.effective_message.chat_id,
                             text=f"Wakeup date?", reply_markup=InlineKeyboardMarkup(keyboard))
    # update.effective_message.reply_text(f"You slept on {readable_datetime(final_sleep_datetime)}\n"
    #                                          f"Now enter your wakeup date.")
    return WAKEUPDATE


def selected_wakeup_date(update: Update, context):
    chat_data = context.chat_data
    today = datetime.today().date()
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    if query.data == 'today':
        chat_data['wakeup_date'] = today
    elif query.data == 'yday':
        chat_data['wakeup_date'] = today - timedelta(days=1)
    elif query.data == 'daybeforeyday':
        chat_data['wakeup_date'] = today - timedelta(days=2)
    elif query.data == 'other':
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /wakesleep again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    else:
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /wakesleep again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    hourwise_keyboard = generate_hour_keyboard()
    update.callback_query.edit_message_text("Wakeup hour?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=hourwise_keyboard))
    return WAKEUPHOUR


def selected_wakeup_hour(update: Update, context):
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    hour_got = query.data.strip()
    logger.info(f'Wakeup hour selected -> {hour_got}')
    keyboard = generate_minute_keyboard(hour=hour_got)
    chat_data['wakeup_hour'] = hour_got
    update.callback_query.edit_message_text("Wakeup final time?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return WAKEUPMINUTE


def selected_wakeup_minute(update: Update, context):
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    date_selected = str(chat_data.get('wakeup_date'))
    time_selected = query.data.strip()
    chat_data['raw_wakeup_time'] = time_selected
    final_wakeup_datetime = datetime.strptime(date_selected + ' ' + time_selected, '%Y-%m-%d %H:%M')
    chat_data['final_wakeup_time'] = final_wakeup_datetime
    logger.info(f"Final selected time for Wakeup -> {final_wakeup_datetime}")
    query_message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id = query_message_id)

    if chat_data['final_wakeup_time'] < chat_data['final_sleep_time']:
        update.effective_message.reply_text("Waking up can happen only after sleeping not before!\nSelect Wakeup date again",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=generate_date_keyboard()))
        return WAKEUPDATE

    # update.callback_query.delete_message(chat_id=update.effective_message.chat_id, hamessage_id=query_message_id)
    context.bot.send_message(chat_id=update.effective_message.chat_id,
                             text=f"Wokeup at: {readable_datetime(final_wakeup_datetime)}")

    context.bot.send_message(chat_id=update.effective_message.chat_id,
                             text=f"Write notes below (else click /skip_notes)")
    # update.effective_message.reply_text(f"You slept on {readable_datetime(final_sleep_datetime)}\n"
    #                                          f"Now enter your wakeup date.")
    return WAKEUP_NOTE


def wakesleep_notes(update, context):
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id-1)
    chat_data = context.chat_data
    ans = update.effective_message.text
    chat_data['wakesleep_notes'] = ans
    if not chat_data.get('wakesleep_notes'):
        chat_data['wakesleep_notes'] = ''
    # update.effective_message.reply_text(f"Note added to your sleep record!\n"
    #                           f"<b>Wakeup time</b> -> {chat_data['wakeup_time']}\n"
    #                           f"<b>Comment</b> -> {chat_data['wakesleep_notes']}", parse_mode='HTML')
    save_wakesleep_record(update, context)
    return ConversationHandler.END


def skip_wakesleep_notes(update, context):
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id-1)
    chat_data = context.chat_data
    if not chat_data.get('wakesleep_notes'):
        chat_data['wakesleep_notes'] = ''
    save_wakesleep_record(update, context)
    return ConversationHandler.END

#TODO THe sleep time should not already exist in db
def save_wakesleep_record(update, context):
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            try:
                final_sleep_time = chat_data['final_sleep_time']
                final_wakeup_time = chat_data['final_wakeup_time']
                wakesleep_notes = chat_data['wakesleep_notes']
                if not isinstance(final_sleep_time, datetime) or not isinstance(final_wakeup_time, datetime):
                    update.effective_message.reply_text("Something went wrong, try /wakesleep again!")
                    logger.info("Something went wrong with datatype of final sleep time and wakeup time, try /wakesleep again!")
                    return ConversationHandler.END
            except:
                update.effective_message.reply_text("Something went wrong, try /wakesleep again!")
                logger.info("Something went wrong, try /wakesleep again!")
                return ConversationHandler.END

            wakesleep_record: Wakesleep = Wakesleep(user_id=user.id, sleeptime=final_sleep_time, wakeuptime=final_wakeup_time,
                            notes=wakesleep_notes, created_at=datetime.now())
            try:
                session.add(wakesleep_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving wakesleep to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /wakesleep again..")
            else:
                session.commit()
                logger.info(f"Wakesleep record added - {wakesleep_record}")
                update.effective_message.reply_text(f"Record added-> \n\n"
                                          f"<b>Slept at:</b> {wakesleep_record.sleeptime}\n"
                                          f"<b>Wokeup at:</b> {wakesleep_record.wakeuptime}\n"
                                          f"<b>Notes:</b>  {wakesleep_record.notes if wakesleep_record.notes else '-'}", parse_mode='HTML')
                clear_chatdata(context=context)


def cancel_wakesleep(update, context):
    update.effective_message.reply_text(f'Wakesleep command cancelled!')
    return ConversationHandler.END


def timeout_wakesleep(update, context):
    update.effective_message.reply_text(f'Wakesleep command timedout! (timeout limit - {wakesleep_timeout_time} sec')
    return ConversationHandler.END


def mywakesleeps(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.wakesleeps.count():
                for _id, item in enumerate(user.wakesleeps.order_by(desc('wakeuptime')).all()):
                    if _id < 5:
                        update.effective_message.reply_text(f"{readable_datetime(item.sleeptime)} - {readable_datetime(item.wakeuptime)}")
                # update.effective_message.reply_text([(str(item.sleeptime), str(item.wakeuptime), item.notes) for item in user.wakesleeps.all()])
            else:
                update.effective_message.reply_text("You haven't added a single sleep record. Use /wakesleep to get started")


wakesleep_handler = ConversationHandler(
    entry_points=[CommandHandler('wakesleep', wakesleep)],
    states={
            SLEEPDATE: [CallbackQueryHandler(selected_sleep_date, pattern='^today|yday|daybeforeyday|other$')],
            SLEEPHOUR: [CallbackQueryHandler(selected_sleep_hour, pattern=generate_pattern_for_wakesleep_hour())],
            SLEEPMINUTE: [CallbackQueryHandler(selected_sleep_minute, pattern=generate_pattern_for_wakesleep_minute())],
            WAKEUPDATE: [CallbackQueryHandler(selected_wakeup_date, pattern='^today|yday|daybeforeyday|other$')],
            WAKEUPHOUR: [CallbackQueryHandler(selected_wakeup_hour, pattern=generate_pattern_for_wakesleep_hour())],
            WAKEUPMINUTE: [CallbackQueryHandler(selected_wakeup_minute, pattern=generate_pattern_for_wakesleep_minute())],
            WAKEUP_NOTE: [MessageHandler(Filters.regex('skip_notes'), skip_wakesleep_notes),
                            MessageHandler(Filters.text, wakesleep_notes)],
            ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_wakesleep)]
    },
    fallbacks=[CommandHandler('cancel_wakesleep', cancel_wakesleep)],
    conversation_timeout=wakesleep_timeout_time
)
