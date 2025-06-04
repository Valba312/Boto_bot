"""Handlers for a simple agency workflow used in ROSFINEX."""

import logging
from telebot.types import Message

from config import ADMIN_IDS
from db import repository as db

logger = logging.getLogger(__name__)


def register(bot):
    """Register bot commands for ROSFINEX."""

    @bot.message_handler(commands=['start'])
    def cmd_start(m: Message):
        """Регистрация пользователя."""
        user_id = m.from_user.id
        name = m.from_user.full_name
        role = 'admin' if user_id in ADMIN_IDS else 'agent'
        db.add_user(user_id, None, name, role)
        bot.reply_to(m, f'Вы зарегистрированы как {role}')

    @bot.message_handler(commands=['newapp'])
    def cmd_newapp(m: Message):
        """Добавление новой заявки.
        Ожидается формат:
        /newapp ФИО; телефон; город; интерес; комментарий
        """
        parts = m.text.split(maxsplit=1)
        if len(parts) < 2:
            return bot.reply_to(
                m,
                'Используйте: /newapp ФИО; телефон; город; интерес; комментарий'
            )
        data = [p.strip() for p in parts[1].split(';')]
        if len(data) < 5:
            return bot.reply_to(m, 'Нужно указать пять полей через ";"')
        full_name, phone, city, interest, comment = data[:5]
        app_id = db.add_application(m.from_user.id, full_name, phone, city, interest, comment)
        bot.reply_to(m, f'Заявка #{app_id} добавлена')

    @bot.message_handler(commands=['myapps'])
    def cmd_myapps(m: Message):
        """Список заявок пользователя."""
        apps = db.get_user_applications(m.from_user.id)
        if not apps:
            return bot.reply_to(m, 'У вас нет заявок')
        lines = [f"{row[0]}: {row[1]} - {row[2]}" for row in apps]
        bot.reply_to(m, '\n'.join(lines))

    @bot.message_handler(commands=['allapps'])
    def cmd_allapps(m: Message):
        """Список всех заявок (администратор)."""
        if m.from_user.id not in ADMIN_IDS:
            return
        apps = db.get_all_applications()
        if not apps:
            return bot.reply_to(m, 'Нет заявок')
        lines = [f"{row[0]}: {row[1]} - {row[2]}" for row in apps]
        bot.reply_to(m, '\n'.join(lines))

    @bot.message_handler(commands=['setstatus'])
    def cmd_setstatus(m: Message):
        """Изменение статуса заявки (администратор)."""
        if m.from_user.id not in ADMIN_IDS:
            return
        parts = m.text.split(maxsplit=2)
        if len(parts) < 3:
            return bot.reply_to(m, 'Используйте: /setstatus id статус')
        try:
            app_id = int(parts[1])
        except ValueError:
            return bot.reply_to(m, 'id должен быть числом')
        status = parts[2].strip()
        db.update_application_status(app_id, status)
        bot.reply_to(m, 'Статус обновлён')

