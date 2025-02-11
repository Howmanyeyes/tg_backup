import logging
import os
import sys
import queue
from logging.handlers import QueueHandler, QueueListener
from collections.abc import Mapping
from typing import Optional, List, Any, Callable, Awaitable

from pydantic import BaseModel, Field
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import BaseMiddleware, types

class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base_message = super().format(record)
        # Check if "kwargs" attribute exists in the log `record`. If yes, format and append them
        if isinstance(record.args, Mapping):
            formatted_kwargs = " || " + ", ".join(f"{key}: {value}" for key, value in record.args.items())
            return base_message + formatted_kwargs
        else:
            return base_message

class NonShitQueueHandler(QueueHandler):
    def prepare(self, record):
        return record

def setup_logger(name: str = 'default',
                encoding: str = 'utf-8',
                stdout: bool = True,
                filepath: str | None = None,
                text_format: str = '%(asctime)s | %(funcName)s | %(levelname)s | %(message)s',
                datefmt: str = '%Y-%m-%dT%H:%M:%S%z',
                level: int | str = 20,
                **kwargs
                 ):
    main_logger = logging.getLogger(name)
    main_logger.setLevel(level=level)
    if main_logger.hasHandlers():
        main_logger.handlers.clear()

    log_queue = queue.Queue(-1)
    queue_handler = NonShitQueueHandler(log_queue)
    main_logger.addHandler(queue_handler)

    if filepath or stdout:
        txtformatter = TextFormatter(fmt= text_format, datefmt=datefmt)

    handlers = []
    if filepath:
        dir = os.path.dirname(filepath)
        os.makedirs(dir, exist_ok=True)
        fileh = logging.FileHandler(filepath, encoding= encoding)
        fileh.setFormatter(txtformatter)
        handlers.append(fileh)
    
    if stdout:
        stdouth = logging.StreamHandler(sys.stdout)
        stdouth.setFormatter(txtformatter)
        handlers.append(stdouth)

    # if logserver_url: cut functionality

    listener = QueueListener(log_queue, *handlers)
    listener.start()
    main_logger.listener = listener
    return main_logger

def buttons(buttons_dict: dict, cols: int = 1) -> InlineKeyboardMarkup:
    """
    Convert a dictionary into an InlineKeyboardMarkup.
    
    For each key-value pair in buttons_dict:
      - If the value is a string, use it as the button label and the key as callback_data.
      - If the value is a dict, expect it to have a "msg" key (for label) and optionally a "url" key.
        If "url" is provided, the button will be created as a URL button.
    
    Args:
        buttons_dict (dict): A dictionary where keys are callback_data and values are either:
                             - A string label, or
                             - A dict with keys "msg" and optionally "url".
    
    Returns:
        InlineKeyboardMarkup: The constructed inline keyboard.
    """
    buttons_list = []
    
    for callback, data in buttons_dict.items():
        if isinstance(data, dict):
            label = data.get("msg", "No message supplied!")
            url = data.get("url")
            if url:
                button = InlineKeyboardButton(text=label, url=url)
            else:
                button = InlineKeyboardButton(text=label, callback_data=callback)
        else:
            # If data is not a dict, treat it as a string label.
            button = InlineKeyboardButton(text=data, callback_data=callback)
        buttons_list.append(button)
    
    rows = [buttons_list[i:i+cols] for i in range(0, len(buttons_list), cols)]

    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    
    return keyboard

class Topic(BaseModel):
    topic_id: int = Field(..., description="Unique identifier for the forum topic (thread)")
    name: str = Field(..., description="Name of the forum topic")

class Chat(BaseModel):
    chat_id: int = Field(..., description="Unique identifier for the chat")
    chat_type: str = Field(..., description="Type of chat: 'private', 'group', 'supergroup', or 'channel'")
    title: Optional[str] = Field(None, description="Title of the chat (if applicable)")
    username: Optional[str] = Field(None, description="Username for the chat (if applicable)")
    topics: Optional[List[Topic]] = Field(None, description="List of forum topics for chats that support topics")

class ChatsStorage(BaseModel):
    chats: List[Chat] = Field(default_factory=list, description="List of chats where the bot is present")
    file_path: str

    def add_chat(self, chat: Chat) -> None:
        """
        Add a new chat or update an existing one by chat_id.
        """
        for idx, existing_chat in enumerate(self.chats):
            if existing_chat.chat_id == chat.chat_id:
                self.chats[idx] = chat
                return
        self.chats.append(chat)

    def delete_chat(self, chat_id: int) -> bool:
        """
        Delete a chat by its chat_id.
        
        Returns:
            bool: True if the chat was found and deleted, False otherwise.
        """
        for idx, existing_chat in enumerate(self.chats):
            if existing_chat.chat_id == chat_id:
                del self.chats[idx]
                return True
        return False

    def save(self) -> None:
        """
        Save the storage to a JSON file.
        """
        with open(self.file_path, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=2))

    def load(self) -> None:
        """
        Load the storage from a JSON file. If the file does not exist, return an empty storage.
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = f.read()
                loaded_storage = self.__class__.model_validate_json(data)
                self.chats = loaded_storage.chats
        except FileNotFoundError:
            self.chats=[]


class ChatTrackingMiddleware(BaseMiddleware):
    def __init__(self, storage: ChatsStorage) -> None:
        """
        :param storage: An instance of ChatsStorage (our Pydantic model container)
        :param file_path: File path to save the updated storage.
        """
        self.storage = storage
        self.file_path = storage.file_path
        super().__init__()

    async def __call__(
        self, 
        handler: Callable[[types.Update, dict[str, Any]], Awaitable[Any]],
        event: types.Update,
        data: dict[str, Any]
    ) -> Any:
        # Check if the update has a message
        if event.chat:
            chat_data = event.chat

            # Create a basic Chat instance from the update.
            new_chat = Chat(
                chat_id=chat_data.id,
                chat_type=chat_data.type,
                title="No title",
                username="No username",
                topics=[]
            )
            if chat_data.username:
                new_chat.username = chat_data.username
            if chat_data.title:
                new_chat.title = chat_data.title

            # If the message is part of a forum thread, update topics.
            if event.message_thread_id:
                new_chat.topics = []
                thread_id = event.message_thread_id

                # If the message signals creation of a forum topic,
                # the update contains a `forum_topic_created` field.
                if event.forum_topic_created:
                    topic_name = event.forum_topic_created.name
                else:
                    topic_name = "Unknown"

                new_topic = Topic(topic_id=thread_id, name=topic_name)
                new_chat.topics.append(new_topic)

            # Look for an existing chat with the same chat_id.
            existing = next((c for c in self.storage.chats if c.chat_id == new_chat.chat_id), None)
            if existing:
                # Merge non-duplicate topics if any new topics are present.
                for topic in new_chat.topics:
                    if not any(t.topic_id == topic.topic_id for t in (existing.topics or [])):
                        if existing.topics is None:
                            existing.topics = []
                        existing.topics.append(topic)
                # Optionally, update title/username if needed.
            else:
                self.storage.add_chat(new_chat)

            # Save the updated storage to file.
            self.storage.save()
        # Continue processing the update.
        return await handler(event, data)
    
if __name__ == "__main__":
    storage = ChatsStorage(file_path="suka.json")
    storage.load()
    
    # Try loading existing storage; if not found, create a new one.

    
    # Add a private chat
    private_chat = Chat(
        chat_id=123456789,
        chat_type="private",
        username="user_example"
    )
    storage.add_chat(private_chat)
    
    # Add a forum-enabled chat with topics
    forum_chat = Chat(
        chat_id=-111345734567456745671155,
        chat_type="supergroup",
        title="Forum Chat",
        topics=[
            Topic(topic_id=1, name="General Discussion"),
            Topic(topic_id=2, name="Announcements")
        ]
    )
    storage.add_chat(forum_chat)
    
    # Save the updated storage to file
    storage.save()
    
    # Save again after deletion
    storage.save()
    print("Current storage:", storage.model_dump_json(indent=2))