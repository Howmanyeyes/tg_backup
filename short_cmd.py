from aiogram import Router, F
from aiogram.types import CallbackQuery

from consts import M, chats
from utils import buttons

MESSAGES = M["fail"]
router = Router()
router.message.filter(F.chat.type == "private")

@router.callback_query(F.data == 'where_am_i')
async def option1_handler(callback: CallbackQuery):
    await callback.answer()
    id = callback.from_user.id
    await callback.bot.send_message(chat_id=id, text=MESSAGES["msg"],
                                    reply_markup=buttons(MESSAGES["buttons"]))