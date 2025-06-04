import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
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

