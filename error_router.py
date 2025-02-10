from telegram import Update
from telegram.ext import MessageHandler, filters, CallbackContext

from consts import M

MESSAGES = M["fail"]

async def handle_unknown_message(update: Update, context: CallbackContext) -> None:
    """
    This handler responds to any unexpected user message.
    """
    # Send a fallback message to the user.
    await update.message.reply_text(
        MESSAGES["msg"]
    )

def register(application):
    """
    Registers the unknown message handler to the application.
    The handler is added with a high group number so that it's checked last.
    """
    # group=100 ensures that this handler is evaluated after other handlers.
    application.add_handler(MessageHandler(filters.ALL, handle_unknown_message), group=100)
