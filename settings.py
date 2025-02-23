from aiogram import Router, F
from aiogram.types import CallbackQuery

from consts import M, chats
from utils import buttons

MESSAGES = M["settings"]
router = Router()
router.message.filter(F.chat.type == "private")

@router.callback_query(F.data == 'where_am_i')
async def where_am_i(callback: CallbackQuery):
    await callback.answer()
    id = callback.from_user.id
    message_privates = "\n".join([x.username for x in chats.chats if x.chat_type == 'private'])
    message_publics = "\n".join([x.title for x in chats.chats if x.chat_type == 'supergroup' or
                                 x.chat_type == 'group'])
    msg = f"\n\nPrivate:\n{message_privates}\n\nPublic:\n{message_publics}"
    await callback.bot.send_message(chat_id=id, text=MESSAGES["where"]["msg"] + msg,
                                    reply_markup=buttons(MESSAGES["where"]["buttons"]))

@router.callback_query(F.data == 'choose_workdir')
async def chosing_workdir(callback: CallbackQuery):
    await callback.answer()
    id = callback.from_user.id
    butt = {f"choice_{x.chat_id}": 
               (x.username if x.chat_type == 'private' else x.title) for x in chats.chats}
    await callback.bot.send_message(chat_id=id, text=MESSAGES["choose_workdir"]["msg"],
                                    reply_markup=buttons(butt))
    
@router.callback_query(F.data.startswith('choice_'))
async def dir_set(callback: CallbackQuery):
    await callback.answer()
    workdir_id = int(callback.data.split('_')[-1])
    chats.workchat = workdir_id
    chats.save()
    workchat = next(filter(lambda x: x.chat_id == workdir_id, chats.chats))
    workchat_name = workchat.username if workchat.chat_type == 'private' else workchat.title
    await callback.message.reply(text=f'{MESSAGES["choose_workdir"]["set_succ"]} {workchat_name}')
    await callback.bot.send_message(chat_id=workdir_id,
                                    text=MESSAGES["choose_workdir"]["set_alert"])
    
@router.callback_query(F.data == 'choose_mode')
async def mode_choise(callback: CallbackQuery):
    await callback.answer()
    await callback.message.reply(text=MESSAGES["mode"]["msg"],
                                 reply_markup=buttons(MESSAGES["mode"]["buttons"]))
    
@router.callback_query(F.data.in_(["archive", "individual"]))
async def mode_set(callback: CallbackQuery):
    chats.mode = callback.data
    chats.save()
    await callback.answer(text=MESSAGES["mode"]["succ"])
    await callback.message.delete()
