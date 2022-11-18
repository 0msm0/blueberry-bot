from telegram.ext import ConversationHandler, CommandHandler, \
    MessageHandler, Filters
from dbhelper import Session
import logging
from models import User, Taskcompleted
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

taskcompleted_timeout_time = 120
TASKS = range(1)

def taskcompleted(update, context):
    logger.info("Inside completed tasks")
    chat_id = update.message.chat_id
    with Session() as session:
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            update.message.reply_text("Write your Completed Tasks. \n\nclick /canceltaskcompleted to cancel\nclick /donetasks after writing")
            return TASKS


def add_completed_tasks(update, context):
    logger.info('enter your completed tasks')
    chat_data = context.chat_data
    thought = update.message.text
    if not chat_data.get('tasks'):
        chat_data['tasks'] = list()
    chat_data['tasks'].append(thought)
    return TASKS


def done_tasks(update, context):
    chat_data = context.chat_data
    if not chat_data.get('tasks'):
        len_of_tasks = 0
        update.message.reply_text("Atleast one task is needed, use /donetasks once done")
        return TASKS
    else:
        len_of_tasks = len(chat_data['tasks'])
    message_id_of_donetasks = update.message.message_id - len_of_tasks - 1
    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_donetasks)
    save_tasks_record(update, context)
    return ConversationHandler.END


def save_tasks_record(update, context):
    logger.info('Inside Tasks record')
    chat_data = context.chat_data
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user: User = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            tasks = chat_data['tasks']
            tasks = ",,,".join(tasks)

            tasks_record: Taskcompleted = Taskcompleted(user_id=user.id, tasks=tasks, created_at=datetime.now())
            try:
                session.add(tasks_record)
            except:
                session.rollback()
                clear_chatdata(context=context)
                logger.error(f"Error saving tasks to database", exc_info=True)
                update.effective_message.reply_text("Something wrong, please try /taskscompleted again..")
            else:
                session.commit()
                logger.info(f"Completed Tasks record added - {tasks_record}")
                update.effective_message.reply_text(f"Record added - \n\n"
                                                    f"{tasks_record.tasks}", parse_mode='HTML')
                update.effective_message.reply_text(f"Use /mytaskcompleted to check previous records")
                try:
                    message_id_of_letsstart = int(chat_data['message_id_of_letsstart'])
                    context.bot.delete_message(chat_id=update.effective_message.chat_id, message_id=message_id_of_letsstart)
                except:
                    clear_chatdata(context=context)
                    logger.exception("error converting chat_data['message_id_of_letsstart'] to int")
            clear_chatdata(context=context)


def canceltaskcompleted(update, context):
    update.effective_message.reply_text('Thought command cancelled!')
    return ConversationHandler.END


def timeout_taskcompleted(update, context):
    update.effective_message.reply_text(f'Taskcompleted command timedout! (timeout limit - {taskcompleted_timeout_time} sec')
    return ConversationHandler.END


def mytaskcompleted(update, context):
    with Session() as session:
        chat_id = update.effective_message.chat_id
        user = get_current_user(chat_id=chat_id, update=update, context=context, session=session)
        if user:
            if user.tasks.count():
                for _id, item in enumerate(user.tasks.order_by('tasks').all()):
                    if _id < 5:
                        update.effective_message.reply_text(f"{_id}. {item.id} {item.tasks.replace(',,,', ', ')}")
            else:
                update.effective_message.reply_text("You haven't added a single completed tasks record. Use /taskcompleted to get started")


taskcompleted_handler = ConversationHandler(
    entry_points=[CommandHandler('taskcompleted', taskcompleted)],
    states={
        TASKS: [CommandHandler('donetasks', done_tasks),
                    MessageHandler(Filters.text, add_completed_tasks)],
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.text and ~Filters.command, timeout_taskcompleted)]
    },
    fallbacks=[CommandHandler('canceltaskcompleted', canceltaskcompleted)],
    conversation_timeout=taskcompleted_timeout_time
)