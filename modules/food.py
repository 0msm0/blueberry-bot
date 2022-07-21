import os

from sqlalchemy import desc
from telegram.ext import ConversationHandler, inlinequeryhandler, CallbackContext, CallbackQueryHandler, CommandHandler, \
    MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram import Update
from dbhelper import Session
import logging
from models import User, Food
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

END = ConversationHandler.END

FOLDERNAME_USERFOODS = 'userfoods/'
if not os.path.isdir(FOLDERNAME_USERFOODS):
    os.mkdir(FOLDERNAME_USERFOODS)

food_timeout_time = 120

FOODDATE, FOODHOUR, FOODMINUTE, FOODNAME, FOOD_NOTE, PHOTO_UPLOAD, FOODLABEL = range(7)

minutes_list = [00, 10, 20, 30, 40, 50]


def generate_label_keyboard():
    keyboard = [[
        InlineKeyboardButton("Morning Breakfast", callback_data="morning_breakfast"),
        InlineKeyboardButton("Lunch", callback_data="lunch"),
        InlineKeyboardButton("Evening Snacks", callback_data="evening_snacks"),
    ],
        [
            InlineKeyboardButton("Dinner", callback_data="dinner"),
            InlineKeyboardButton("Night Snacks", callback_data="night_snacks"),
            InlineKeyboardButton("Other", callback_data="other"),
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


def generate_pattern_for_food_hour():
    temp = ''
    for hour in range(24):
        temp += str(hour) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def generate_pattern_for_food_minute():
    temp = ''
    for hour in range(24):
        for minute in minutes_list:
            temp += str(hour) + ':' + str(minute) + '|'
    temp = temp[:-1]
    final_pattern = '^' + temp + '$'
    return final_pattern


def food(update, context):
    logger.info("Inside food")
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.timezones.count():
                keyboard = generate_date_keyboard()
                update.message.reply_text("Let's start. (use /cancelfood if you want to cancel)")
                update.message.reply_text("Date of food?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                query_message_id = update.message.message_id + 1
                chat_data = context.chat_data
                chat_data['message_id_of_letsstart'] = query_message_id
                return FOODDATE
    # query_message_id = update.message.message_id
    # context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id = query_message_id)


def selected_food_date(update: Update, context):
    logger.info("inside selected food date")
    chat_data = context.chat_data
    today = datetime.today().date()
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    if query.data == 'today':
        chat_data['food_date'] = today
    elif query.data == 'yday':
        chat_data['food_date'] = today - timedelta(days=1)
    elif query.data == 'daybeforeyday':
        chat_data['food_date'] = today - timedelta(days=2)
    elif query.data == 'other':
        update.effective_message.reply_text("This function is yet to be handled.\n Use /food again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    else:
        update.effective_message.reply_text("This function is yet to be handled.\n Use /food again to enter recent logs.")  # TODO - handle this
        return ConversationHandler.END
    hourwise_keyboard = generate_hour_keyboard()
    update.callback_query.edit_message_text("Hour of food?", reply_markup=InlineKeyboardMarkup(inline_keyboard=hourwise_keyboard))
    return FOODHOUR


def selected_food_hour(update: Update, context):
    logger.info("inside selected food hour")
    chat_data = context.chat_data
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    hour_got = query.data.strip()
    logger.info(f'Food hour selected -> {hour_got}')
    keyboard = generate_minute_keyboard(hour=hour_got)
    chat_data['food_hour'] = hour_got
    update.callback_query.edit_message_text("Time of food?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return FOODMINUTE


def selected_food_minute(update: Update, context: CallbackContext):
    logger.info("inside selected food minute")
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    date_selected = str(chat_data.get('food_date'))
    time_selected = query.data.strip()
    chat_data['food_time'] = time_selected
    food_datetime = datetime.strptime(date_selected + ' ' + time_selected, '%Y-%m-%d %H:%M')
    chat_data['food_time'] = food_datetime
    logger.info(f"Selected time for Food -> {food_datetime}")
    update.callback_query.edit_message_text("Enter Food name. \n\n use /doneitems once complete")
    return FOODNAME


def food_name(update, context):
    logger.info("inside food name")
    foodname = update.message.text
    chat_data = context.chat_data
    if not chat_data.get('food_item'):
        chat_data['food_item'] = list()
    chat_data['food_item'].append(foodname)
    return FOODNAME


def doneitems(update, context):
    chat_data = context.chat_data
    if not chat_data.get('food_item'):
        len_of_food_items = 0
        update.message.reply_text("Atleast one item is needed, use /doneitems once done")
        return FOODNAME
    else:
        len_of_food_items = len(chat_data['food_item'])

    message_id_of_doneitems = update.message.message_id - len_of_food_items -1
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_doneitems)
    update.message.reply_text("Write notes below (else click /skip_notes")
    return FOOD_NOTE


def food_notes(update, context):
    logger.info('enter food note')
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    chat_data = context.chat_data
    ans = update.effective_message.text
    chat_data['food_notes'] = ans
    # update.message.reply_text("Notes added successfully.")
    update.message.reply_text("Upload photos if any, else click /donephotos")
    # save_food_record(update, context)
    return PHOTO_UPLOAD


def skip_food_notes(update, context):
    query_message_id = update.effective_message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=query_message_id - 1)
    chat_data = context.chat_data
    if not chat_data.get('food_notes'):
        chat_data['food_notes'] = ''
    update.message.reply_text("Add photo. Once photo done use  /donephotos")
    return PHOTO_UPLOAD


def submit_food_photo(update, context):
    logger.info("inside submit food photo")
    chat_data = context.chat_data
    update.message.reply_text("Photo received. Processing")
    our_file = update.effective_message.photo[-1]
    if our_file:
        try:
            file_id = our_file.file_id
            # file_unique_id = our_file.file_unique_id
            actual_file = our_file.get_file()

            filepath_to_download = actual_file['file_path']

            ext = filepath_to_download.split('.')[-1]
            filename_to_store = f"{file_id}.{ext}"

            logger.info(f"Inside /submitfoodphoto. Got photo. Saving photo as- {filename_to_store}")
            update.message.reply_chat_action(action=constants.CHATACTION_UPLOAD_PHOTO)

            status = save_file_locally(filepath_to_download=filepath_to_download,
                                       filename_to_store=filename_to_store)

            if status:
                update.message.reply_text('Photo uploaded successfully..')
            else:
                update.message.reply_text("Photo not uploaded. Plz try again!")
                chat_data.clear()
                return ConversationHandler.END

            if not chat_data.get('food_photo_temp'):
                chat_data['food_photo_temp'] = list()
            final_file_path = f"{FOLDERNAME_USERFOODS}{filename_to_store}"
            chat_data['food_photo_temp'].append(final_file_path)
            logger.info(
                f"Inside /submitfoodphoto. Got photo. Final food photos - {chat_data['food_photo_temp']}")
        except:
            logger.error(f"Update {update} caused error WHILE SAVING PHOTO- {context.error}")
            logger.error(f"Exception while saving photo", exc_info=True)
            chat_data.clear()
            return ConversationHandler.END
    update.message.reply_text('Photo processed, successfully!')
    return PHOTO_UPLOAD


def save_file_locally(filepath_to_download, filename_to_store):
    logger.info("inside save file locally")

    response = requests.get(filepath_to_download)
    final_file_path = f"{FOLDERNAME_USERFOODS}{filename_to_store}"
    try:
        logger.info(f"Inside /addlog. Saving photo locally")
        with open(final_file_path, 'wb') as f:
            f.write(response.content)
        logger.info("photo Saved locally..")
        return True
    except:
        logger.info("photo could not be saved locally..")
        return False


def only_photo_accepted(update, context):
    update.message.reply_text("Only photos are accepted. Submit photo of your food!")
    return PHOTO_UPLOAD


def donephotos(update, context):
    logger.info('inside donephoto')
    chat_data = context.chat_data
    if not chat_data.get('food_photo_temp'):
        len_of_food_photos = 0
        chat_data['food_photos'] = None
    else:
        len_of_food_photos = len(chat_data['food_photo_temp'])
        chat_data['food_photos'] = ',,,'.join(chat_data['food_photo_temp'])

    message_id_of_doneitems = update.message.message_id - len_of_food_photos -1
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_doneitems)

    keyboard = generate_label_keyboard()
    update.message.reply_text("Select food label", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    return FOODLABEL


def selected_label(update: Update, context):
    logger.info('Inside selected')
    query: inlinequeryhandler = update.callback_query
    update.callback_query.answer()
    chat_data = context.chat_data
    chat_data['food_label'] = query.data
    query_message_id = update.callback_query.message.message_id
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id = query_message_id)

    # query.edit_message_text(text=f"Label recieved = {chat_data['food_label']}")

    # data = f"date={chat_data['food_time']}\n" \
    #        f"items={chat_data['food_item']}\n" \
    #        f"notes={chat_data['food_notes']}\n" \
    #        f"photos={chat_data['photos']}\n" \
    #        f"label={chat_data['food_label']}"
    # update.effective_message.reply_text(f'context_data = {data}')
    save_food_record(update, context)
    return ConversationHandler.END


def save_food_record(update, context):
    logger.info('Inside food record')
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            food_time = chat_data['food_time']
            food_item = chat_data['food_item']
            food_item = ",,,".join(food_item)
            food_notes = chat_data['food_notes']
            food_photos = chat_data['food_photos']
            food_label = chat_data['food_label']

            # print(user.id, food_time, food_item, food_notes, food_photos, food_label)
            food_record: Food = Food(user_id=user.id, food_time=food_time, food_item=food_item, food_notes=food_notes,
                                     food_photos=food_photos, food_label=food_label, created_at=datetime.now())
            try:
                session.add(food_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving food to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /food again..")
            else:
                session.commit()
                logger.info(f"Food record added - {food_record}")
                update.effective_message.reply_text(f"Record added - \n\n"
                                                    f"<b>Food taken at:</b> {readable_datetime(food_record.food_time)}\n"
                                                    f"<b>Food items:</b> {food_record.food_item}\n"
                                                    f"<b>Food label:</b> {food_record.food_label}\n"
                                                    f"<b>Notes:</b>  {food_record.food_notes if food_record.food_notes else '-'}", parse_mode='HTML')
                try:
                    message_id_of_letsstart = int(chat_data['message_id_of_letsstart'])
                    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_letsstart)
                except:
                    clear_chatdata(context=context)
                    logger.exception("error converting chat_data['message_id_of_letsstart'] to int")
            clear_chatdata(context=context)


def cancelfood(update, context):
    update.effective_message.reply_text('Food command cancelled!')
    return END


def timeout_food(update, context):
    update.effective_message.reply_text(f'Food command timedout! (timeout limit - {food_timeout_time} sec')
    return ConversationHandler.END


def readable_datetime(inputdatetime: datetime):
    return inputdatetime.strftime('%d %b, %H:%M')


def myfood(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.foods.count():
                for _id, item in enumerate(user.foods.order_by(desc('food_time')).all()):
                    if _id < 5:
                        update.effective_message.reply_text(f"{_id}. {item.id} {readable_datetime(item.food_time)} - {item.food_item.replace(',,,', ', ')}")
                # update.effective_message.reply_text([(str(item.sleeptime), str(item.wakeuptime), item.notes) for item in user.wakesleeps.all()])
            else:
                update.effective_message.reply_text("You haven't added a single sleep record. Use /food to get started")

food_handler = ConversationHandler(
    entry_points=[CommandHandler('food', food)],
    states={
        FOODDATE: [CallbackQueryHandler(selected_food_date, pattern='^today|yday|daybeforeyday|other$')],
        FOODHOUR: [CallbackQueryHandler(selected_food_hour, pattern=generate_pattern_for_food_hour())],
        FOODMINUTE: [CallbackQueryHandler(selected_food_minute, pattern=generate_pattern_for_food_minute())],
        FOODNAME: [CommandHandler('doneitems', doneitems),
                   MessageHandler(Filters.text and ~Filters.command, food_name)],
        FOOD_NOTE: [CommandHandler('skip_notes', skip_food_notes),
                    MessageHandler(Filters.text, food_notes)],
        PHOTO_UPLOAD: [CommandHandler('donephotos', donephotos),
                       MessageHandler(Filters.photo, submit_food_photo),
                       MessageHandler(Filters.text, only_photo_accepted)],
        FOODLABEL: [CallbackQueryHandler(selected_label,
                                         pattern='^morning_breakfast|lunch|evening_snacks|dinner|night_snacks|other$')],

        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_food)]
    },
    fallbacks=[CommandHandler('cancelfood', cancelfood)],
    conversation_timeout=food_timeout_time
)