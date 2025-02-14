from aiogram import Router, types, F

from consts import M
from utils import buttons

MESSAGES = M["fail"]
router = Router()

@router.message(F.chat.type == "private")
async def unknown_private_message_handler(message: types.Message):
    """
    Handles any unrecognized message by sending a default response.
    """
    await message.answer(text=MESSAGES["msg_private"],
                         reply_markup=buttons(MESSAGES["buttons_private"]))
