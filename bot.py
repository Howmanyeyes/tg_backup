import logging
from telegram.ext import ApplicationBuilder

from consts import BOT_TOKEN, logger
import error_router, start_router

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_router.register(application)

    error_router.register(application)

    # Start the bot in polling mode
    application.run_polling()

if __name__ == '__main__':
    main()
