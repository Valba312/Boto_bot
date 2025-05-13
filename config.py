import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "tasks.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")