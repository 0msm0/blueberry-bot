from telegram.ext import ConversationHandler, CommandHandler, \
    MessageHandler, Filters
from dbhelper import Session
import logging
from models import User, Thoughts
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

thought_timeout_time = 120
THOUGHTS = range(1)

def thoughts(update, context):
    logger.info("Inside thoughts")
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            # update.message.reply_text("Let's start. (use /cancelthoughts if you want to cancel)")
            # chat_data = context.chat_data
            update.message.reply_text("Write your Thoughts. \n\nclick /cancelthought to cancel\nclick /donethoughts after writing")
            return THOUGHTS


def add_thoughts(update, context):
    logger.info('enter your thoughts')
    chat_data = context.chat_data
    thought = update.message.text
    if not chat_data.get('thoughts'):
        chat_data['thoughts'] = list()
    chat_data['thoughts'].append(thought)
    return THOUGHTS


def done_thought(update, context):
    chat_data = context.chat_data
    if not chat_data.get('thoughts'):
        len_of_thoughts = 0
        update.message.reply_text("Atleast one thought is needed, use /donethought once done")
        return THOUGHTS
    else:
        len_of_thoughts = len(chat_data['thoughts'])
    message_id_of_donethoughts = update.message.message_id - len_of_thoughts - 1
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_donethoughts)
    save_thoughts_record(update, context)
    return ConversationHandler.END


def save_thoughts_record(update, context):
    logger.info('Inside Thoughts record')
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            thoughts = chat_data['thoughts']
            thoughts = ",,,".join(thoughts)

            thoughts_record: Thoughts = Thoughts(user_id=user.id, thoughts=thoughts, created_at=datetime.now())
            try:
                session.add(thoughts_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving thoughts to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /thoughts again..")
            else:
                session.commit()
                logger.info(f"Thoughts record added - {thoughts_record}")
                update.effective_message.reply_text(f"Record added - \n\n"
                                                    f"{thoughts_record.thoughts}", parse_mode='HTML')
                update.effective_message.reply_text(f"Use /mythought to check previous records")
                try:
                    message_id_of_letsstart = int(chat_data['message_id_of_letsstart'])
                    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_letsstart)
                except:
                    clear_chatdata(context=context)
                    logger.exception("error converting chat_data['message_id_of_letsstart'] to int")
            clear_chatdata(context=context)


def cancelthought(update, context):
    update.effective_message.reply_text('Thought command cancelled!')
    return ConversationHandler.END


def timeout_thought(update, context):
    update.effective_message.reply_text(f'Thought command timedout! (timeout limit - {thought_timeout_time} sec')
    return ConversationHandler.END


def mythought(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.thoughts.count():
                for _id, item in enumerate(user.thoughts.order_by('thoughts').all()):
                    if _id < 5:
                        update.effective_message.reply_text(f"{_id}. {item.thoughts.replace(',,,', ', ')}")
            else:
                update.effective_message.reply_text("You haven't added a single thoughts record. Use /thoughts to get started")


thoughts_handler = ConversationHandler(
    entry_points=[CommandHandler('thought', thoughts)],
    states={
        THOUGHTS: [CommandHandler('donethought', done_thought),
                    MessageHandler(Filters.text and ~Filters.command, add_thoughts)],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_thought)]
    },
    fallbacks=[CommandHandler('cancelthought', cancelthought)],
    conversation_timeout=thought_timeout_time
)