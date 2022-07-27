from sqlalchemy import desc
import os
from telegram.ext import ConversationHandler, inlinequeryhandler, CallbackContext, CallbackQueryHandler, CommandHandler, \
    MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram import Update
from dbhelper import Session
import logging

from models import User, Gym
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

gym_timeout_time = 120
GYM_DATE, GYM_HOUR, GYM_MINUTE, GYM_NAME, GYM_SET, GYM_WEIGHT, GYM_REPETITION, GYM_NOTE = range(8)
minutes_list = [00, 10, 20, 30, 40, 50]
gym_names = ['Biceps', 'Calf Raise', 'Chest', 'Deadlift', 'Planks', 'Pullups', 'Pushups', 'Shoulder', 'Shrugs', 'Squats', 'Triceps', 'Other']

def generate_gym_names_keyboard():
    super_keys = []
    keys = []
    rowlimit = 4
    no_of_keys_in_row = 0

    for item in gym_names:
        key = InlineKeyboardButton(f"{item}", callback_data=str(item).lower())
        if no_of_keys_in_row == rowlimit:
            super_keys.append(keys.copy())  # [[01,12,23,34]]
            keys.clear()
            no_of_keys_in_row = 0
        keys.append(key)
        no_of_keys_in_row += 1
    super_keys.append(keys.copy())
    return super_keys


def generate_pattern_for_gym_names():
    temp = ''
    for item in gym_names:
        temp += str(item).lower() + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


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


def generate_set_keyboard():
    super_keys = []
    keys = []
    rowlimit = 5
    no_of_keys_in_row = 0
    for set in range(1,6):
        key = InlineKeyboardButton(f"{set}", callback_data=str(set))
        if no_of_keys_in_row == rowlimit:
            super_keys.append(keys.copy())
            keys.clear()
            no_of_keys_in_row = 0
        keys.append(key)
        no_of_keys_in_row += 1
    super_keys.append(keys.copy())
    return super_keys


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


def generate_weight_keyboard():
    super_keys = []
    keys = []
    rowlimit = 5
    no_of_keys_in_row = 0
    for weight in range(1,16):
        key = InlineKeyboardButton(f"{weight} kg", callback_data=str(weight))
        if no_of_keys_in_row == rowlimit:
            super_keys.append(keys.copy())
            keys.clear()
            no_of_keys_in_row = 0
        keys.append(key)
        no_of_keys_in_row += 1
    super_keys.append(keys.copy())
    return super_keys


def generate_pattern_for_gym_hour():
    temp = ''
    for hour in range(24):
        temp += str(hour) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def generate_pattern_for_gym_minute():
    temp = ''
    for hour in range(24):
        for minute in minutes_list:
            temp += str(hour) + ':' + str(minute) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def generate_pattern_for_set():
    temp = ''
    for set in range(1,5):
        temp += str(set) + '|'
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


def generate_pattern_for_weights():
    temp = ''
    for weight in range(1,16):
        temp += str(weight) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern





def gym(update, context):
    logger.info("Inside gym")
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.timezones.count():
                keyboard = generate_date_keyboard()
                update.message.reply_text("Let's start. (use /cancelgym if you want to cancel)")
                update.message.reply_text("Date of Gym Exercise?",
                                          reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                query_message_id = update.message.message_id + 1
                chat_data = context.chat_data
                chat_data['message_id_of_letsstart'] = query_message_id
                return GYM_DATE


def selected_gym_date(update: Update, context):
    logger.info("inside selected gym date")
    chat_data = context.chat_data
    today = datetime.today().date()
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    if query.data == 'today':
        chat_data['gym_date'] = today
    elif query.data == 'yday':
        chat_data['gym_date'] = today - timedelta(days=1)
    elif query.data == 'daybeforeyday':
        chat_data['gym_date'] = today - timedelta(days=2)
    elif query.data == 'other':
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /gym again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    else:
        update.effective_message.reply_text(
            "This function is yet to be handled.\n Use /gym again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    hourwise_keyboard = generate_hour_keyboard()
    update.callback_query.edit_message_text("Hour of Gym exercise?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=hourwise_keyboard))
    return GYM_HOUR

def selected_gym_hour(update: Update, context):
    logger.info("inside selected gym exercise hour")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    hour_got = query.data.strip()
    logger.info(f'Gym hour selected -> {hour_got}')
    chat_data['gym_hour'] = hour_got
    keyboard = generate_minute_keyboard(hour=hour_got)
    update.callback_query.edit_message_text("Time of Gym exercise?",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return GYM_MINUTE

def selected_minute_for_gym(update: Update, context: CallbackContext):
    logger.info("inside selected gym exercise minute")
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    date_selected = str(chat_data.get('gym_date'))
    time_selected = query.data.strip()
    chat_data['gym_time'] = time_selected
    gym_datetime = datetime.strptime(date_selected + ' ' + time_selected, '%Y-%m-%d %H:%M')
    chat_data['gym_datetime'] = gym_datetime
    logger.info(f"Selected time for Gym Exercise -> {gym_datetime}")
    gym_keyboard = generate_gym_names_keyboard()
    update.callback_query.edit_message_text("Select type of Gym exercise",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=gym_keyboard))
    return GYM_NAME

def selected_gymname(update, context):
    logger.info('Inside selected gym type')
    query: inlinequeryhandler = update.callback_query
    chat_data = context.chat_data
    update.callback_query.answer()
    gym_name = query.data.strip()
    chat_data['gym_name'] = gym_name
    gym_type = str(chat_data.get('gym_name'))
    chat_data['gym_type'] = gym_type
    logger.info(f'Gym Exercise Type -> {gym_type}')
    keyboard = generate_set_keyboard()
    update.callback_query.edit_message_text("Enter Sets of Gym",
                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return GYM_SET


def gym_set(update, context):
    logger.info("inside selected set count")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    total_sets = query.data.strip()
    logger.info(f'Set count -> {total_sets}')
    chat_data['total_sets'] = total_sets
    total_set = int(total_sets)
    chat_data['total_set'] = total_set
    if not chat_data.get('current_set'):
        chat_data['current_set'] = 1
    repetition_keyboard = generate_repetitions_keyboard()
    update.callback_query.edit_message_text(f"How many repetition in set #{chat_data['current_set']}",
                                                reply_markup=InlineKeyboardMarkup(inline_keyboard=repetition_keyboard))
    return GYM_REPETITION


def gym_repetition(update, context):
    logger.info("inside selected repetition count")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    repetition = query.data.strip()
    logger.info(f'Repetition count -> {repetition}')
    if not chat_data.get('repetition'):
        chat_data['repetition'] = list()
    chat_data['repetition'].append(repetition)
    weight_keyborad = generate_weight_keyboard()
    update.callback_query.edit_message_text(f"What weight for set #{chat_data['current_set']} in kgs",
                                           reply_markup=InlineKeyboardMarkup(inline_keyboard=weight_keyborad))
    return GYM_WEIGHT


def gym_weight(update, context):
    logger.info("inside selected weight count")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    weight = query.data.strip()
    logger.info(f'weight count -> {weight}')
    if not chat_data.get('weight'):
        chat_data['weight'] = list()
    chat_data['weight'].append(weight)
    if not chat_data.get('current_set'):
        chat_data['current_set'] = 1
    else:
        chat_data['current_set'] += 1
    if chat_data['current_set'] <= chat_data['total_set']:
        repetition_keyboard = generate_repetitions_keyboard()
        update.callback_query.edit_message_text(f"How many repetition in set #{chat_data['current_set']}",
                                                reply_markup=InlineKeyboardMarkup(inline_keyboard=repetition_keyboard))
        return GYM_REPETITION
    else:
        update.callback_query.edit_message_text("Write notes below (else click /skip_notes)")
        return GYM_NOTE

def gym_notes(update, context):
    chat_data = context.chat_data
    logger.info('enter gym note')
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    ans = update.effective_message.text
    chat_data['gym_notes'] = ans
    update.message.reply_text("Notes added successfully.")
    save_gym_record(update, context)
    return ConversationHandler.END

def skip_gym_notes(update, context):
    chat_data = context.chat_data
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    chat_data = context.chat_data
    chat_data['gym_notes'] = ''
    save_gym_record(update, context)
    return ConversationHandler.END


def cancelgym(update, context):
    update.effective_message.reply_text('Gym command cancelled!')
    clear_chatdata(context=context)
    return ConversationHandler.END


def save_gym_record(update, context):
    logger.info('Inside Gym record')
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            gym_datetime = chat_data['gym_datetime']
            gym_type = chat_data['gym_type']
            total_set = chat_data['total_set']
            repetition = chat_data['repetition']
            repetition = ", ".join(repetition)
            weight = chat_data['weight']
            weight = ", ".join(weight)
            gym_notes = chat_data['gym_notes']
            gym_record: Gym = Gym(user_id=user.id, gym_datetime=gym_datetime, gym_type=gym_type,
                                     total_set=total_set, repetition=repetition, weight=weight, gym_notes=gym_notes, created_at=datetime.now())
            try:
                session.add(gym_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving gym to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /gym again..")
            else:
                session.commit()
                logger.info(f"Gym record added - {gym_record}")
                update.effective_message.reply_text(f"Record added - \n\n"
                                                    f"<b>At:</b> {readable_datetime(gym_record.gym_datetime)}\n"
                                                    f"<b>Type:</b> {gym_record.gym_type}\n"
                                                    f"<b>Sets:</b> {gym_record.total_set}\n"
                                                    f"<b>Reps:</b> {gym_record.repetition}\n"
                                                    f"<b>Weight:</b> {gym_record.weight}\n"
                                                    f"<b>Notes:</b>  {gym_record.gym_notes if gym_record.gym_notes else '-'}", parse_mode='HTML')
                update.effective_message.reply_text(f"Use /mygym to check previous records")
                try:
                    message_id_of_letsstart = int(chat_data['message_id_of_letsstart'])
                    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_letsstart)
                except:
                    clear_chatdata(context=context)
                    logger.exception("error converting chat_data['message_id_of_letsstart'] to int")
            clear_chatdata(context=context)

def get_reps_and_weights_in_format(reps, weights):
    reps = reps.split(', ')
    weights = weights.split(', ')
    if isinstance(reps, list):
        temp = ''
        for rep, weight in zip(reps, weights):
            temp += f"{weight}kg - {rep} reps\n"
    else:
        temp = f"{weights}kg - {reps} reps"
    return temp

def mygym(update: Update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.gyms.count():
                for _id, item in enumerate(user.gyms.order_by(desc('gym_datetime')).all()):
                    if _id < 5:
                        rep_weight_string = get_reps_and_weights_in_format(item.repetition, item.weight)
                        if not item.gym_notes:
                            update.effective_message.reply_text(f"<b>{item.gym_type}</b> - {item.total_set} sets\n"
                                                                f"{rep_weight_string}"
                                                                f"{readable_datetime(item.gym_datetime)}\n\n", parse_mode='HTML')
                        else:
                            update.effective_message.reply_text(f"<b>{item.gym_type}</b> - {item.total_set} sets\n"
                                                                f"{rep_weight_string}"
                                                                f"Note - {item.gym_notes}\n"
                                                                f"{readable_datetime(item.gym_datetime)}\n\n", parse_mode='HTML')
            # update.effective_message.reply_text([(str(item.gym_datetime), item.gym_notes) for item in user.gym.all()])
            else:
                print('in here')
                update.effective_message.reply_text("You haven't added a single Gym exercise record. Use /gym to get started")


def timeout_gym(update, context):
    update.effective_message.reply_text(f'Gym command timedout! (timeout limit - {gym_timeout_time} sec')
    return ConversationHandler.END


def readable_datetime(inputdatetime: datetime):
    return inputdatetime.strftime('%d %b, %H:%M')


gym_handler = ConversationHandler(
    entry_points=[CommandHandler('gym', gym)],
    states={
        GYM_DATE: [CallbackQueryHandler(selected_gym_date, pattern='^today|yday|daybeforeyday|other$')],
        GYM_HOUR: [CallbackQueryHandler(selected_gym_hour, pattern=generate_pattern_for_gym_hour())],
        GYM_MINUTE: [CallbackQueryHandler(selected_minute_for_gym, pattern=generate_pattern_for_gym_minute())],
        GYM_NAME: [CallbackQueryHandler(selected_gymname, pattern=generate_pattern_for_gym_names())],
        GYM_SET: [CallbackQueryHandler(gym_set, pattern=generate_pattern_for_set())],
        GYM_REPETITION: [CallbackQueryHandler(gym_repetition, pattern=generate_pattern_for_repetitions())],
        GYM_WEIGHT: [CallbackQueryHandler(gym_weight, pattern=generate_pattern_for_weights())],
        GYM_NOTE: [CommandHandler('skip_notes', skip_gym_notes),
                    MessageHandler(Filters.text, gym_notes)],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_gym)]
    },
    fallbacks=[CommandHandler('cancelgym', cancelgym)],
    conversation_timeout=gym_timeout_time
)