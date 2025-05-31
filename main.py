import os
import logging
import threading
import time
import schedule
from logging.handlers import RotatingFileHandler
from telebot import TeleBot
from telebot.apihelper import ApiTelegramException

from config import TOKEN, LOG_LEVEL
from db.repository import (
    create_tables,
    get_tasks,
    delete_task_by_message_id,
    get_cached_message_ids,
    update_cache,
    create_cache_table
)

# Инициализация бота и БД
bot = TeleBot(TOKEN, parse_mode="HTML")
create_tables()
create_cache_table()

# Импорт хендлеров
import handlers.new_task
import handlers.filter
import handlers.callback_accept
import handlers.callback_status
import handlers.callback_task
import handlers.callback_navigation

handlers.new_task.register(bot)
handlers.filter.register(bot)
handlers.callback_accept.register(bot)
handlers.callback_status.register(bot)
handlers.callback_task.register(bot)
handlers.callback_navigation.register(bot)

# Логгирование
def setup_logging():
    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        filename="logs/bot.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8"
    )
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logging.basicConfig(level=LOG_LEVEL, handlers=[file_handler, stream_handler])

setup_logging()
logger = logging.getLogger(__name__)

# Проверка сообщений (живы ли они в Telegram)
def check_deleted_messages():
    logger.info("[ЗАДАЧА] Проверка сообщений началась")

    tasks = get_tasks(full=True)
    cached_ids = get_cached_message_ids()

    for task in tasks:
        mid = task["message_id"]
        cid = task["chat_id"]

        # Пропускаем, если недавно уже проверяли
        if mid in cached_ids:
            continue

        try:
            bot.edit_message_reply_markup(chat_id=cid, message_id=mid)
            update_cache(cid, mid)
        except ApiTelegramException as e:
            if "message to edit not found" in str(e):
                delete_task_by_message_id(mid)
                logger.info(f"[УДАЛЕНО ИЗ БД] message_id={mid}")
            else:
                logger.warning(f"[API ОШИБКА] message_id={mid} ➜ {e}")
        except Exception as e:
            logger.exception(f"[НЕИЗВЕСТНАЯ ОШИБКА] mid={mid}")

    logger.info("[ЗАДАЧА] Проверка завершена")

# Планировщик
schedule.every().day.at("01:00").do(check_deleted_messages)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)

threading.Thread(target=run_scheduler, daemon=True).start()

# Пинг-файл (для watchdog)
def ping_watchdog():
    while True:
        with open('bot.ping', 'w') as f:
            f.write(str(int(time.time())))
        time.sleep(60)

threading.Thread(target=ping_watchdog, daemon=True).start()

# Запуск бота
bot.infinity_polling()