import os
from dotenv import load_dotenv

load_dotenv()

# Токен Telegram-бота обязательно должен быть задан
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
 mmc10t-codex/разработать-telegram-бота-для-агентской-системы-rosfinex
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set")

DB_PATH = os.getenv("DB_PATH", "tasks.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Список id администраторов через запятую
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(',') if x]

# Если переменная окружения не задана, сразу сообщаем о проблеме.
if not TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN not configured. Проверьте переменные окружения"
    )
DB_PATH = os.getenv("DB_PATH", "tasks.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Список администраторов через запятую, например "123,456"
ADMIN_IDS = {
    int(uid)
    for uid in os.getenv("ADMIN_IDS", "").split(",")
    if uid.strip().isdigit()
}
 main

