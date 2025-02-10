from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from consts import M

MESSAGES = M["start"]
router = Router()

@router.message(Command(commands=["start", "menu"]))
async def start_menu_handler(message: types.Message):
    """
    Sends the welcome message and displays the bot's menu.
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Option 1"), KeyboardButton(text="Option 2")],
            [KeyboardButton(text="Option 3")]
        ],
        resize_keyboard=True,
    )
    await message.answer(
        MESSAGES["msg"],
        reply_markup=keyboard
    )
