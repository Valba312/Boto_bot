import os
import logging
from logging.handlers import RotatingFileHandler
from telebot import TeleBot
import threading
import time

from config import TOKEN, LOG_LEVEL
from db.repository import create_tables

# Импорт хендлеров
import handlers.new_task
import handlers.filter
import handlers.callback_accept
import handlers.callback_task
import handlers.rosfinex

def ping_watchdog():
    while True:
        with open('bot.ping', 'w') as f:
            f.write(str(int(time.time())))
        time.sleep(60)

# Запуск пинг-ватчдога (фоновый поток)
threading.Thread(target=ping_watchdog, daemon=True).start()

def setup_logging():
    """Настройка логирования в файл с ротацией + в консоль"""
    os.makedirs("logs", exist_ok=True)

    file_handler = RotatingFileHandler(
        filename="logs/bot.log",
        maxBytes=1_000_000,      # 1 МБ на файл
        backupCount=5,           # максимум 5 файлов: bot.log, bot.log.1, ..., bot.log.5
        encoding="utf-8"
    )

    # Преобразуем LOG_LEVEL к int, если оно строка
    level = getattr(logging, LOG_LEVEL, logging.INFO) if isinstance(LOG_LEVEL, str) else LOG_LEVEL

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            file_handler,
            logging.StreamHandler()  # вывод в консоль
        ]
    )

    # Отключаем лишний DEBUG от сторонних библиотек
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telebot").setLevel(logging.INFO)

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("🚀 Запуск Telegram-бота")

    # Сохраняем PID процесса
    with open('bot.pid', 'w') as f:
        f.write(str(os.getpid()))

    # Создание экземпляра бота
    bot = TeleBot(TOKEN, parse_mode='HTML')

    # Создание таблиц в базе данных
    create_tables()

    # Регистрация всех хендлеров
    handlers.new_task.register(bot)
    handlers.filter.register(bot)
    handlers.callback_accept.register(bot)
    handlers.callback_task.register(bot)
    handlers.rosfinex.register(bot)

    # Запуск polling
    bot.remove_webhook()
    bot.infinity_polling()

if __name__ == '__main__':
    main()