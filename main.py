import os
import logging
from logging.handlers import RotatingFileHandler
from telebot import TeleBot

from config import TOKEN, LOG_LEVEL
from db.repository import create_tables

# Импорт хендлеров
import handlers.new_task
import handlers.filter
import handlers.callback_accept
import handlers.callback_status
import handlers.callback_task
import handlers.callback_navigation


def setup_logging():
    """Настройка логирования в файл с ротацией + в консоль"""
    os.makedirs("logs", exist_ok=True)

    file_handler = RotatingFileHandler(
        filename="logs/bot.log",
        maxBytes=1_000_000,      # 1 МБ на файл
        backupCount=5,           # максимум 5 файлов: bot.log, bot.log.1, ..., bot.log.5
        encoding="utf-8"
    )

    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            file_handler,
            logging.StreamHandler()  # вывод в консоль
        ]
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("🚀 Запуск Telegram-бота")

    # Создание экземпляра бота
    bot = TeleBot(TOKEN, parse_mode='HTML')

    # Создание таблиц в базе данных
    create_tables()

    # Регистрация всех хендлеров
    handlers.new_task.register(bot)
    handlers.filter.register(bot)
    handlers.callback_accept.register(bot)
    handlers.callback_status.register(bot)
    handlers.callback_task.register(bot)
    handlers.callback_navigation.register(bot)

    # Запуск polling
    bot.remove_webhook()
    bot.infinity_polling()


if __name__ == '__main__':
    main()
