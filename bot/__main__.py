import asyncio
import os

import uvloop
from dotenv import load_dotenv
from pyrogram import Client
from telegram.ext import Application

from .support_bot import SupportBot

load_dotenv()
uvloop.install()

TELEGRAM_STRING_SESSION = os.environ.get("TELEGRAM_STRING_SESSION")
TELEGRAM_API_KEY = os.environ.get("TELEGRAM_API_KEY")
USER_APP_ID = os.environ.get("USER_APP_ID")
USER_APP_HASH = os.environ.get("USER_APP_HASH")
USER_ACCOUNT_NAME = os.environ.get("USER_ACCOUNT_NAME")


async def main() -> None:
    support_bot = SupportBot(
        telegram_bot=Application.builder().token(TELEGRAM_API_KEY).build(),
        user_bot=Client(
            USER_ACCOUNT_NAME,
            api_id=USER_APP_ID,
            api_hash=USER_APP_HASH,
            session_string=TELEGRAM_STRING_SESSION,
        ),
    )
    try:
        await support_bot.start()
    finally:
        await support_bot.stop()


asyncio.run(main())
