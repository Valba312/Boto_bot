import os
from dotenv import load_dotenv

load_dotenv()

# Токен Telegram-бота обязательно должен быть задан
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set")

# Путь к базе данных и уровень логирования
DB_PATH = os.getenv("DB_PATH", "tasks.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Список идентификаторов администраторов через запятую
ADMIN_IDS = {
    int(uid)
    for uid in os.getenv("ADMIN_IDS", "").split(",")
    if uid.strip().isdigit()
}

