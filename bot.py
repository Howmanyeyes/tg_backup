import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from consts import BOT_TOKEN, logger, chats
from utils import ChatTrackingMiddleware
import error_router, start_router, settings, backup

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.message.middleware(ChatTrackingMiddleware(chats))

    dp.include_router(start_router.router)

    dp.include_router(settings.router)
    dp.include_router(backup.router)

    dp.include_router(error_router.router)
    

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
