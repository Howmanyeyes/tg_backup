import os
import datetime

from aiogram import Router, F
from aiogram.types import Message

from consts import M, chats
from utils import buttons, get_size, create_backup, send_backup_files

MESSAGES = M["backup"]
router = Router()
router.message.filter(F.chat.type == "private")

@router.message(F.text.regexp(r"^(?:[A-Za-z]:\\|/).+"))
async def start_backup(message: Message):
    if not os.path.exists(message.text):
        message.answer(text=MESSAGES["error"])
        return
    path = message.text
    await message.reply(text=MESSAGES["preparation"])
    size, est_time = get_size(path)
    create_backup(path)
    msg = f'{MESSAGES["msg"]} \n\n {size} \n\n will aproximately take: {est_time}' 
    await message.reply(text=msg)
    for chat in chats.chats:
        if chat.chat_id == chats.workchat:
            work = chat
    if work.chat_type == 'supergroup':
        today = datetime.date.today()
        thread_name = f"backup - {today.strftime('%d.%m.%Y')}"
        
        # Create the forum topic; ensure your bot is an admin with can_manage_topics permission.
        forum_topic = await message.bot.create_forum_topic(chat_id=work.chat_id, name=thread_name)
        thread_id = forum_topic.message_thread_id
        
        await message.bot.send_message(chat_id=work.chat_id,
                                       text="Кира, тут твоя структура папок",
                                       message_thread_id=thread_id)
        
        send_backup_files(message.bot, work.chat_id, thread_id=thread_id)
        await message.reply(text=MESSAGES["done"])
        
    else:
        today = datetime.date.today()
        thread_name = f"backup - {today.strftime('%d.%m.%Y')}"
        await message.bot.send_message(chat_id=work.chat_id,
                                text="Кира тут твоя структура папок")
        send_backup_files(message.bot, work.chat_id)
        await message.reply(text=MESSAGES["done"])
