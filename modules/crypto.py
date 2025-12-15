"""
Crypto wallet management conversation handler.

Requires python-telegram-bot v21+
"""
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from dbhelper import Session
from models import User, Crypto
from modules.getcurrentuser import get_current_user
from modules.helpers import clear_chat_data
from utils.logger import get_logger

logger = get_logger(__name__)

# Conversation states
WALLET = 0

# Configuration
TIMEOUT_SECONDS = 120


async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for crypto wallet setup."""
    logger.info("Inside crypto")
    chat_id = update.message.chat_id

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if user:
            await update.message.reply_text(
                "You get rewarded RoutineBotToken for adding your logs.\n\n"
                "Enter your wallet (polygon below). Click /idonthavewallet if you don't have one."
            )
            return WALLET

    return ConversationHandler.END


async def addwallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wallet address input."""
    logger.info("Enter your wallet")
    chat_data = context.chat_data
    wallet_addr = update.message.text.strip()

    if len(wallet_addr) != 42:
        await update.message.reply_text(
            "Doesn't look like wallet address. Try /crypto again."
        )
        return ConversationHandler.END

    if not chat_data.get('wallet'):
        chat_data['wallet'] = []
    chat_data['wallet'].append(wallet_addr)

    await save_crypto_record(update, context)
    return ConversationHandler.END


async def save_crypto_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save crypto wallet record to database."""
    logger.info("Inside Crypto record saving")
    chat_data = context.chat_data
    chat_id = update.effective_chat.id

    with Session() as session:
        user = User.get_user_by_chat_id(session, chat_id)
        if user:
            wallet = chat_data.get('wallet', [])
            wallet_str = ",,,".join(wallet)

            wallet_record = Crypto(
                user_id=user.id,
                wallet=wallet_str,
                created_at=datetime.now()
            )

            try:
                session.add(wallet_record)
                session.commit()

                logger.info(f"Crypto record added - {wallet_record}")
                await update.effective_message.reply_text(
                    f"Record added -\n\n{wallet_record.wallet}",
                    parse_mode="HTML"
                )
                await update.effective_message.reply_text(
                    "Use /mycrypto to check previous records"
                )

                # Try to delete the "let's start" message
                message_id = chat_data.get('message_id_of_letsstart')
                if message_id:
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id,
                            message_id=int(message_id)
                        )
                    except Exception:
                        logger.exception("Error deleting letsstart message")

            except Exception as e:
                session.rollback()
                logger.error(f"Error saving wallet to database: {e}", exc_info=True)
                await update.effective_message.reply_text(
                    "Something wrong, please try /crypto again."
                )
            finally:
                clear_chat_data(context)


async def idonthavewallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle users without wallet."""
    await update.effective_message.reply_text(
        "No worries. Watch this 5 min video on http://cryptochimaru.com "
        "and get your own wallet with some test tokens."
    )
    return ConversationHandler.END


async def cancelcrypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel crypto setup."""
    await update.effective_message.reply_text("Crypto command cancelled")
    return ConversationHandler.END


async def timeout_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle conversation timeout."""
    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"Crypto command timed out! (timeout limit - {TIMEOUT_SECONDS} sec)"
        )
    return ConversationHandler.END


async def mycrypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's crypto wallets."""
    chat_id = update.effective_message.chat_id

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if user:
            if user.cryptos.count():
                for idx, item in enumerate(user.cryptos.order_by('wallet').all()):
                    if idx < 5:
                        await update.effective_message.reply_text(
                            f"{idx}. {item.wallet.replace(',,,', ', ')}"
                        )
            else:
                await update.effective_message.reply_text(
                    "You haven't added any wallet.\n\n"
                    "Use /crypto to add wallet.\n"
                    "Use /idonthavewallet to get tips."
                )


async def mycryptorewards(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show crypto rewards info."""
    chat_id = update.message.chat_id

    with Session() as session:
        user = await get_current_user(chat_id, update, context, session)
        if user:
            await update.message.reply_text(
                "Your rewards in RoutineBotToken will be shown here. "
                "We are working on the logic, but it'll be in relation with "
                "your number of daily logs, so keep adding logs and come back here later."
            )


# Build the conversation handler
crypto_handler = ConversationHandler(
    entry_points=[CommandHandler('crypto', crypto)],
    states={
        WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, addwallet)],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout_crypto)]
    },
    fallbacks=[
        CommandHandler('idonthavewallet', idonthavewallet),
        CommandHandler('cancelcrypto', cancelcrypto),
    ],
    conversation_timeout=TIMEOUT_SECONDS
)
