import asyncio
import logging
import uvloop
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, ContextTypes
from pyrogram import Client
from telegram import Update
from os import environ
import threading
from pyrogram import Client
import signal
from types import FrameType
from typing import List, Set, Optional
from dataclasses import dataclass, field
import re
import random
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo
import json
import openai
import sys
import traceback

load_dotenv()
uvloop.install()

TELEGRAM_API_KEY = environ["TELEGRAM_API_KEY"]

USER_APP_ID = environ["USER_APP_ID"]
USER_APP_HASH = environ["USER_APP_HASH"]
USER_ACCOUNT_NAME = environ["USER_ACCOUNT_NAME"]
HANDLED_SIGNALS = (
    signal.SIGINT,  # Unix signal 2. Sent by Ctrl+C.
    signal.SIGTERM,  # Unix signal 15. Sent by `kill <pid>`.
)
CHAT_ID = int(os.environ.get("CHAT_ID"))
SUPPORT_BOT_ID = os.environ.get("SUPPORT_BOT_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LIST_OF_ADJECTIVES = json.loads(os.environ.get("LIST_OF_ADJECTIVES"))

# Set up logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the ErrorCatcher class
class ErrorCatcher:
    def __init__(self, error_message: Optional[str]=None):
        # Set the exception hook to the custom handle_exception method
        sys.excepthook = self.handle_exception
        self.error_message = error_message

    def handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        # Custom exception handling logic
        no_traceback_error_message = f"Some sad error occurred:\nError type: {exc_type.__name__}\nProblem: {exc_value}\n"
        logger.error(no_traceback_error_message)
        logger.error(f"Traceback: {traceback.print_tb(exc_traceback)}")
        self.error_message = no_traceback_error_message

    async def notify_telegram_channel(self, telegram_client, chat_id) -> None:
        # Method to notify a Telegram channel about the error
        await telegram_client.send_message(chat_id, text=self.error_message)

# Define the AIBody dataclass
@dataclass
class AIBody:
    messages: Optional[list] = None
    temperature: float = 0.6
    model: str  = "gpt-3.5-turbo"

    def form_man_prompt(self, list_of_adjectives: list, username) -> None:
        # Method to form the prompt for AI processing
        first_adj, second_adj, third_adj = random.sample(list_of_adjectives, k=3)

        self.messages = [
            {
                "role": "user",
                "content": f"Опиши  @{username} по прилагательным {first_adj}, {second_adj}, {third_adj} в четырех приложениях, упоминая @{username} один раз за весь текст."
            }
        ]

# Define the AIProcessor dataclass
@dataclass
class AIProcessor:
    api_key: str
    aibody: AIBody = field(default_factory=AIBody)

    async def form_text_to_send(self):
        # Method to process AI completion and form the text to send
        openai.api_key = OPENAI_API_KEY
        completion = openai.ChatCompletion.create(**self.aibody.__dict__)
        text_to_send = completion["choices"][0]["message"]["content"]+"\n\nПарни, теперь ваша очередь говорить комлименты!"
        return text_to_send

# Define the User dataclass
@dataclass
class User:
    id: int
    username: str

# Define the Users dataclass
@dataclass
class Users:
    all_chat_users: List[User]

    def get_recently_mentioned_users(self, merged_string_from_last_messages:str) -> set:
        # Method to extract recently mentioned users from the merged string
        pattern = r"@([A-Za-z0-9_]+)"
        matches = re.findall(pattern, merged_string_from_last_messages)
        return set(matches)
    
    def random_pick_user(self, recently_mentioned_users: Set[str]) -> str:
        # Method to randomly pick a user from the list of all users excluding recently mentioned users
        set_of_all_usernames = {user.username for user in self.all_chat_users}
        users_to_process = set_of_all_usernames.difference(recently_mentioned_users)
        if users_to_process:
            return random.choice(list(users_to_process))
        else:
            return random.choice(list(set_of_all_usernames))

# Define the TelegramUserInterface dataclass
@dataclass
class TelegramUserInterface:
    client: Client
    users: Users = field(default_factory=list)
    history_limit: int = 400
    message_limit: int = 30

    async def get_channel_messages_in_one_string(self, chat_id, support_bot_id) -> str:
        # Method to get the channel messages and merge them into one string
        bot_support_history = [
            message async for message in self.client.get_chat_history(chat_id=chat_id, limit=self.history_limit)
            if message.from_user.id == int(support_bot_id)
        ]
        limited_history = bot_support_history[:self.message_limit]
        test = " ".join([message.text for message in limited_history])
        print(test)  # Limiting the number of messages to process
        return " ".join([message.text for message in limited_history])

    async def get_channel_users(self, chat_id) -> None:
        # Method to retrieve all users in the channel
        self.users = Users([
            User(chat_user.user.id, chat_user.user.username) 
            async for chat_user in self.client.get_chat_members(chat_id=chat_id) 
            if not chat_user.user.is_bot
        ])

# Define the SupportBot class
class SupportBot:
    def __init__(self, telegram_bot: Application, user_bot: Client):
        self.telegram_bot = telegram_bot
        self.user_bot = user_bot
        self.should_exit = asyncio.Event()

    def register_telegram_bot_handlers(self):
        # Method to register Telegram bot handlers
        logger.info("Registering telegram-bot handlers...")
        self.telegram_bot.add_handler(CommandHandler("stop_support", self.stop_support_handler))
        self.telegram_bot.add_handler(CommandHandler("start_support", self.start_support_handler))

    async def stop_support_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Handler for the "/stop_support" command
        chat_id = str(update.message.chat.id)
        logging.info(f"this is chat_id from the stop handle: {chat_id}")
        job_removed = await remove_job_if_exists(chat_id, context)
        text = "Парни больше не поддерживают друг друга в этом чате!" if job_removed else "Никакой поддержки в чате нет."
        await update.message.reply_text(text)

    async def start_support_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Handler for the "/start_support" command
        chat_id = update.message.chat.id
        if not chat_id == CHAT_ID:
            await update.message.reply_text("Сори бро/сис, можно запускать только в особенном чате.")
            return

        if await check_job_exist(chat_id, context):
            await update.message.reply_text("Друг, мужской круг поддержки уже запущен в этом чате. Тыкать больше не надо.")

        time_to_send = datetime.now(tz=ZoneInfo('UTC')) + timedelta(seconds=10)
        await update.message.reply_text("Привет, круг мужской поддержки запущен. Братан, держись и держи мужиков.")
        context.job_queue.run_daily(
            support_message, 
            time=time_to_send, 
            chat_id=chat_id, 
            name=str(chat_id), 
            data={"user_client":self.user_bot, "bot_client": self.telegram_bot}
            )
        #context.job_queue.run_repeating(support_message,interval=15, first=3, chat_id=chat_id, name=str(chat_id), data=self.user_bot)

    async def telegram_bot_start(self):
        # Start the Telegram bot
        logger.info("Starting Telegram bot")
        await self.telegram_bot.initialize()
        await self.telegram_bot.start()
        await self.telegram_bot.updater.start_polling()

        await self.should_exit.wait()

        logger.info("Done starting Telegram bot")

    async def telegram_bot_stop(self):
        # Stop the Telegram bot
        logger.info("Stopping Telegram bot")
        if self.telegram_bot.updater.running:
            await self.telegram_bot.updater.stop()

        await self.telegram_bot.stop()
        await self.telegram_bot.shutdown()
    
    async def start(self):
        # Run the SupportBot
        logger.info("Running SupportBot")

        self.install_signal_handlers()
        self.register_telegram_bot_handlers()

        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(self.telegram_bot_start())
            task_group.create_task(self.user_bot.start())

    async def stop(self):
        # Stop the SupportBot
        logger.info("Shutting down SupportBot...")
        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(self.telegram_bot_stop())
            task_group.create_task(self.user_bot.stop())

    def install_signal_handlers(self) -> None:
        # Install signal handlers for graceful shutdown
        if threading.current_thread() is not threading.main_thread():
            # Signals can only be listened to from the main thread.
            return

        loop = asyncio.get_event_loop()

        try:
            for sig in HANDLED_SIGNALS:
                loop.add_signal_handler(sig, self.handle_exit, sig, None)
        except NotImplementedError:  # pragma: no cover
            # Windows
            for sig in HANDLED_SIGNALS:
                signal.signal(sig, self.handle_exit)

    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
        # Handle the exit signal
        self.should_exit.set()


async def check_job_exist(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # Check if a job with the given chat ID exists
    existing_jobs_ids = {
        job.chat_id
        for job in context.job_queue.jobs()
    }
    logger.info(f"this is ids of existing jobs {existing_jobs_ids}")
    if chat_id in existing_jobs_ids:
        logger.info("The job with this id already exists, no need to add another one.")
        return True

    return False

async def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # Remove a job with the given name
    current_jobs = context.job_queue.get_jobs_by_name(name)

    if not current_jobs:
        return False

    for job in current_jobs:
        logger.info(f"This is the id of chat and the current job: {job.chat_id}")
        job.schedule_removal()        

    return True

async def support_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    # Send the support message
    telegram_user_client = context.job.data["user_client"]
    telegram_bot_client = context.job.data["bot_client"]
    print(telegram_bot_client)
    app = TelegramUserInterface(telegram_user_client)
    await app.get_channel_users(CHAT_ID)
    merged_string = await app.get_channel_messages_in_one_string(chat_id=context.job.chat_id, support_bot_id=SUPPORT_BOT_ID)

    recently_mentioned_set = app.users.get_recently_mentioned_users(merged_string)
    logger.info(f"users recently mentioned by bot: {recently_mentioned_set}")

    aiprocessor = AIProcessor(api_key=OPENAI_API_KEY)
    aiprocessor.aibody.form_man_prompt(LIST_OF_ADJECTIVES, app.users.random_pick_user(recently_mentioned_set))
    logger.info(f"Message to form prompt from: {aiprocessor.aibody.messages[0]['content']}")
    try:
        text_to_send = await aiprocessor.form_text_to_send()
    except Exception as e:
        logger.exception(f"An error occurred during AI processing: {e}")
    else:
        logger.info(f"Message to send: {text_to_send}")
        await telegram_user_client.send_message(chat_id=context.job.chat_id, text=text_to_send)


