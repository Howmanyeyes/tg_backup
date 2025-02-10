from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, CallbackContext

from consts import M

MESSAGES = M["start"]

async def start_menu(update: Update, context: CallbackContext) -> None:
    """
    Sends a welcome message along with a menu.
    """
    welcome_text = "Welcome to our bot! Please choose an option from the menu below:"
    # Define a simple menu keyboard with placeholder buttons.
    menu_keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Option 1"), KeyboardButton("Option 2")],
            [KeyboardButton("Option 3")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await update.message.reply_text(welcome_text, reply_markup=menu_keyboard)

def register(application) -> None:
    """
    Registers the /start and /menu command handlers to show the starting menu.
    """
    application.add_handler(CommandHandler("start", start_menu))
    application.add_handler(CommandHandler("menu", start_menu))
