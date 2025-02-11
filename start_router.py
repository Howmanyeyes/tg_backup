from aiogram import Router, types, F
from aiogram.filters import Command

from consts import M
from utils import buttons

MESSAGES = M["start"]
router = Router()
router.message.filter(F.chat.type == "private")

@router.message(Command(commands=["start", "menu"]))
@router.callback_query(F.data == "menu")
async def start_menu_handler(update: types.Update) -> None:
    """
    Sends the welcome message and displays the bot's menu.
    """
    if type(update) == types.CallbackQuery:
        await update.answer()
        id = update.from_user.id
        await update.bot.send_message(chat_id=id, text=MESSAGES["msg"],
                                      reply_markup=buttons(MESSAGES["buttons"], cols=1))
    else:
        await update.answer(MESSAGES["msg"], reply_markup=buttons(MESSAGES["buttons"], cols=1))

        
