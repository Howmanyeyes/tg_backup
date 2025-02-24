import os
import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from consts import M, chats, logger, backups
from utils import get_size, buttons
from backup import send_backup_files, create_backup, download

MESSAGES = M["backup"]
router = Router()
router.message.filter(F.chat.type == "private")

@router.message(F.text.regexp(r"^(?:[A-Za-z]:\\|/).+"))
async def start_backup(message: Message):
    if not os.path.exists(message.text):
        await message.answer(text=MESSAGES["error"])
        return
    path = message.text
    await message.reply(text=MESSAGES["preparation"])
    size, est_time = get_size(path)
    backup_token = create_backup(path, chats.mode)
    msg = f'{MESSAGES["msg"]} \n\n {size} \n\n will aproximately take: {est_time}' 
    await message.reply(text=msg)
    for chat in chats.chats:
        if chat.chat_id == chats.workchat:
            work = chat
    logger.info("New backup starting")
    if work.chat_type == 'supergroup':
        today = datetime.date.today()
        thread_name = f"backup - {today.strftime('%d.%m.%Y')}"
        
        # Create the forum topic; ensure your bot is an admin with can_manage_topics permission.
        forum_topic = await message.bot.create_forum_topic(chat_id=work.chat_id, name=thread_name)
        thread_id = forum_topic.message_thread_id
        
        await message.bot.send_message(chat_id=work.chat_id,
                                       text="Кира, тут твоя структура папок",
                                       message_thread_id=thread_id,
                                       reply_markup=buttons({
                                           f"download_{backup_token}": MESSAGES["download"]
                                       }))
        
        send_backup_files(message.bot, work.chat_id, thread_id=thread_id, backup_token=backup_token)
        await message.reply(text=MESSAGES["done"])
        logger.info("Backup done")
        
    else:
        today = datetime.date.today()
        thread_name = f"backup - {today.strftime('%d.%m.%Y')}"
        await message.bot.send_message(chat_id=work.chat_id,
                                text="Кира тут твоя структура папок",
                                reply_markup=buttons({
                                           f"download_{backup_token}": MESSAGES["download"]
                                       }))
        send_backup_files(message.bot, work.chat_id, backup_token=backup_token)
        await message.reply(text=MESSAGES["done"])
        logger.info("Backup done")

@router.callback_query(F.data.startswith('download_'))
async def download_backup(callback: CallbackQuery):
    backup_id = callback.data.split("_")[-1]
    result = await download(backup_id, callback.bot)
    if not result:
        await callback.reply(text=MESSAGES["fail_down"])
        return
    await callback.bot.send_message(chat_id=callback.from_user.id,
                                    text = MESSAGES["succ_down"])