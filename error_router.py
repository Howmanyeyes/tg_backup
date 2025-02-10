from aiogram import Router, types

from consts import M

MESSAGES = M["fail"]
router = Router()

@router.message()
async def unknown_message_handler(message: types.Message):
    """
    Handles any unrecognized message by sending a default response.
    """
    await message.answer(
        MESSAGES["msg"]
    )
    # Stop further processing of this update.
    # raise CancelHandler()