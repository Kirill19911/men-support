import logging
import os
import sys
import asyncio

from dotenv import load_dotenv
from telegram.ext import Application
from pyrogram import Client

from .support_bot import SupportBot, ErrorCatcher
import uvloop

load_dotenv()
uvloop.install()

TELEGRAM_API_KEY = os.environ.get("TELEGRAM_API_KEY")
CHAT_ID = int(os.environ.get("CHAT_ID"))
USER_APP_ID = os.environ.get("USER_APP_ID")
USER_APP_HASH = os.environ.get("USER_APP_HASH")
USER_ACCOUNT_NAME = os.environ.get("USER_ACCOUNT_NAME")


def handle_exception(exc_type, exc_value, exc_traceback):
    # Custom exception handler
    # You can modify this function to handle exceptions as per your application's requirements
    logging.error("An unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))   
sys.excepthook = handle_exception


async def main() -> None:
    error_catcher = ErrorCatcher()
    support_bot = SupportBot(
        telegram_bot=Application.builder().token(TELEGRAM_API_KEY).build(),
        user_bot=Client(USER_ACCOUNT_NAME, api_id=USER_APP_ID, api_hash=USER_APP_HASH)
    )
    try:
        await support_bot.start()
    finally:
        #func didn't work for some reason
        #await error_catcher.notify_telegram_channel(support_bot.user_bot, CHAT_ID)
        await support_bot.stop()
        

asyncio.run(main())
