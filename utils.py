import logging
import os
import sys
import queue
from logging.handlers import QueueHandler, QueueListener
from collections.abc import Mapping
from typing import Any, Callable, Awaitable

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import BaseMiddleware, types

from storage import ChatsStorage, Chat, Topic
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
        self.storage.load()
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

def get_size(path: str) -> int:
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # Skip if it is a symbolic link (optional)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return human_readable_size(total_size), estimated_backup_time(total_size)
    else:
        raise ValueError("The provided path is neither a file nor a directory.")
    
def human_readable_size(size_bytes: int) -> str:
    """
    Convert a file size in bytes into a human-readable string with the most relevant unit.
    
    Args:
        size_bytes (int): Size in bytes.
    
    Returns:
        str: Human-readable size string (e.g. "50.5 GB").
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.1f} MB"
    elif size_bytes < 1024**4:
        return f"{size_bytes / 1024**3:.1f} GB"
    else:
        return f"{size_bytes / 1024**4:.1f} TB"
    
def estimated_backup_time(size_bytes: int, upload_speed_mbps: float = 1.5) -> str:
    """
    Calculate the estimated backup time for a given size in bytes at a specified upload speed.
    
    Args:
        size_bytes (int): Total size of the data in bytes.
        upload_speed_mbps (float): Upload speed in megabits per second (Mb/s). Default is 4.7 Mb/s.
    Returns:
        str: The estimated time as a string (e.g. "2h 15m 30.0s").
    """
    # Convert size from bytes to bits
    total_bits = size_bytes * 8
    # Convert upload speed from Mb/s to bits per second (using SI: 1 Mb = 1,000,000 bits)
    speed_bps = upload_speed_mbps * 1_000_000
    # Calculate total seconds required to upload the data
    total_seconds = total_bits / speed_bps

    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds:.1f}s"
    elif minutes > 0:
        return f"{minutes}m {seconds:.1f}s"
    else:
        return f"{seconds:.1f}s"
