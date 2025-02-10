import json

import yaml

from logs import setup_logger

with open("SETTINGS.yaml", "r", -1, "utf-8") as file:
    config = yaml.safe_load(file)
BOT_TOKEN = config.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in SETTINGS.yaml")

logger = setup_logger(name='tg_backuper', filepath='logs/log.log')

with open("messages.json", "r") as file:
    M = json.load(file)