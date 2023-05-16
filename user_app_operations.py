from pyrogram import Client
from typing import List, Set
from dataclasses import dataclass, field
import random
import re


@dataclass
class User:
    id: int
    username: str

#class is used for getting the list of recenlty used users and new support
@dataclass
class Users:
    all_chat_users: List[User]

    #if no matches are found method will return empty set
    def get_recently_mentioned_users(self, merged_string_from_last_messages:str) -> set:
        pattern = r"@([A-Za-z0-9_]+)"
        matches = re.findall(pattern, merged_string_from_last_messages)
        return set(matches)
    
    def random_pick_user(self, recently_mentioned_users: Set[str]) -> str:
        set_of_all_usernames = {user.username for user in self.all_chat_users}
        users_to_process = set_of_all_usernames.difference(recently_mentioned_users)
        if users_to_process:
            return random.choice(list(users_to_process))
        else:
            return random.choice(list(set_of_all_usernames))


@dataclass
class TelegramUserInterface:
    client: Client
    users: Users = field(default_factory=list)
    history_limit: int = 150
    message_limit: int = 15

    #get messages in hisory of a chat and merge it's text in one string
    async def get_channel_messages_in_one_string(self, chat_id, support_bot_id) -> str:
        async with self.client as app:
            bot_support_history = [
                message async for message in app.get_chat_history(chat_id=chat_id, limit=self.history_limit)
                if message.from_user.id == int(support_bot_id)
            ]
            # messages are limited to not go over all memebers of channel for support by .message_limit attribute
            limited_history = bot_support_history[:self.message_limit]
            return " ".join([message.text for message in limited_history])

    #retrieve all users and aassign it to .users attribute
    async def get_channel_users(self, chat_id) -> None:
        async with self.client as app:
            self.users  = Users([
                User(chat_user.user.id, chat_user.user.username) 
                async for chat_user in app.get_chat_members(chat_id=chat_id) 
                if not chat_user.user.is_bot
                ])
            
