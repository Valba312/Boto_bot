import os
from dotenv import load_dotenv

load_dotenv()

# Токен Telegram-бота обязательно должен быть задан
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set")

DB_PATH = os.getenv("DB_PATH", "tasks.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Список id администраторов через запятую
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(',') if x]

