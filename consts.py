import json
import platform

import yaml

from utils import setup_logger, ChatsStorage

with open("SETTINGS.yaml", "r", -1, "utf-8") as file:
    config = yaml.safe_load(file)
BOT_TOKEN = config.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in SETTINGS.yaml")

logger = setup_logger(name='tg_backuper', filepath='logs/log.log')

with open("messages.json", "r", encoding='utf-8') as file:
    M = json.load(file)

OS_NAME = platform.system()

chats = ChatsStorage(file_path="chats.json")
chats.load()