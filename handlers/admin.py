"""Обработчики административных команд и справки."""

import logging
from telebot.types import Message
from config import ADMIN_IDS
from db import repository as db
from utils import throttling_decorator, is_admin

logger = logging.getLogger(__name__)


def register(bot):
    """Регистрация хендлеров команд /start, /help и /stats."""

    @throttling_decorator
    @bot.message_handler(commands=['start', 'help'])
    def cmd_start(m: Message):
        """Отправляет краткую справку по работе бота."""
        help_text = (
            "Добро пожаловать!\n"
            "Доступные команды:\n"
            "/t <текст> — добавить задачу\n"
            "/f — показать невыполненные задачи\n"
            "/stats — статистика (только для администраторов)"
        )
        bot.reply_to(m, help_text, message_thread_id=m.message_thread_id)

    @throttling_decorator
    @bot.message_handler(commands=['stats'])
    def cmd_stats(m: Message):
        """Выводит статистику по задачам (для администраторов)."""
        if not is_admin(m.from_user.id):
            return bot.reply_to(m, "❌ Доступ запрещён", message_thread_id=m.message_thread_id)

        cid = m.chat.id
        tid = m.message_thread_id
        try:
            total = len(db.get_all_tasks(cid, tid))
            accepted = len(db.get_tasks_by_status(cid, tid, 'принято'))
            pending = len(db.get_tasks_by_status(cid, tid, 'не выполнено'))
            bot.reply_to(
                m,
                f"Всего задач: {total}\nПринято: {accepted}\nНе выполнено: {pending}",
                message_thread_id=tid,
            )
        except Exception:
            logger.exception("Ошибка получения статистики")
            bot.reply_to(m, "❗ Не удалось получить статистику", message_thread_id=tid)

