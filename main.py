import logging
import os
import sys
import random
import json

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import pytz
import openai
from pyrogram import Client

# For sendging requests to Telegram from userbot since bots can't retrive users' names and history
from user_app_operations import TelegramUserInterface
import uvloop

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LIST_OF_ADJECTIVES = json.loads(os.environ.get("LIST_OF_ADJECTIVES"))
TELEGRAM_API_KEY = os.environ.get("TELEGRAM_API_KEY")
CHAT_ID = int(os.environ.get("CHAT_ID"))
SUPPORT_BOT_ID = os.environ.get("SUPPORT_BOT_ID")
TEST_TIME = datetime.now() + timedelta(seconds=120)

USER_APP_ID = os.environ.get("USER_APP_ID")
USER_APP_HASH = os.environ.get("USER_APP_HASH")
USER_ACCOUNT_NAME = os.environ.get("USER_ACCOUNT_NAME")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
def handle_exception(exc_type, exc_value, exc_traceback):
    # Custom exception handler
    # You can modify this function to handle exceptions as per your application's requirements
    logging.error("An unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))   
sys.excepthook = handle_exception

@dataclass
class AIBody:
    messages: Optional[list] = None
    temperature: float = 0.7
    model: str  = "gpt-3.5-turbo"

    def form_man_prompt(self, list_of_adjectives: list, username) -> None:
        first_adj, second_adj, third_adj = random.choices(list_of_adjectives, k=3)

        self.messages = [{"role": "user", "content": f"Опиши  @{username} \
        по прилагательным {first_adj}, {second_adj}, {third_adj} в четырех приложениях, упоминая @{username} один раз."}]


async def support_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the support message."""
    uvloop.install()
    app = TelegramUserInterface(Client(USER_ACCOUNT_NAME, api_id=USER_APP_ID, api_hash=USER_APP_HASH))
    await app.get_channel_users(CHAT_ID)
    merged_string = await app.get_channel_messages_in_one_string(chat_id=CHAT_ID, support_bot_id=SUPPORT_BOT_ID)

    recently_mentioned_set = app.users.get_recently_mentioned_users(merged_string)
    logging.info(f"users recently mentgioed by bot: {recently_mentioned_set}")


    aibody = AIBody()
    aibody.form_man_prompt(LIST_OF_ADJECTIVES, app.users.random_pick_user(recently_mentioned_set))
    logging.info(f"Message to form prompt from: {aibody.messages[0]['content']}")
    openai.api_key = OPENAI_API_KEY
    completion = openai.ChatCompletion.create(**aibody.__dict__)
    logging.info(f'Message to send to the channel: {completion["choices"][0]["message"]["content"]}')
    job = context.job
    await context.bot.send_message(job.chat_id, text=completion["choices"][0]["message"]["content"])


async def start_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    chat_id = update.message.chat.id
    if not chat_id == CHAT_ID:
        await update.message.reply_text("Сори бро/сис, можно запускать только в особенном чате.")
        return
    logging.info(chat_id)
    time_to_run = time(hour=TEST_TIME.hour, minute=TEST_TIME.minute, second=TEST_TIME.second, tzinfo=pytz.timezone('Asia/Kuala_Lumpur'))
    logging.info(f"time to run: {time_to_run}")
    await update.message.reply_text("Привет, круг мужской поддержки запущен. Братан, держись и держи мужиков.")
    context.job_queue.run_daily(support_message, time=time_to_run, 
            days=(0, 1, 2, 3, 4, 5, 6), chat_id=chat_id, name=str(chat_id))



def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    logging.info(f"This is the id of chat and the current job: {current_jobs}")
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def stop_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = str(update.message.chat.id)
    logging.info(f"this is cha_id from the stop handle: {chat_id}")
    job_removed = remove_job_if_exists(chat_id, context)
    text = "Парни больше не поддерживают друг друга в этом чате!" if job_removed else "Никакой поддержки в чате нет."
    await update.message.reply_text(text)


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_API_KEY).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start_support", start_support))
    application.add_handler(CommandHandler("stop_support", stop_support))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()