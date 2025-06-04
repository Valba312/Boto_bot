"""Handlers for a simple agency workflow used in ROSFINEX."""

import logging
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton

from config import ADMIN_IDS
from db import repository as db
import re

_NEW_APP_DATA = {}


def _main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Новая заявка", "Мои заявки")
    return kb

def _help_text(role: str) -> str:
    base = (
        "Доступные команды:\n"
        "Новая заявка — создать заявку (/newapp)\n"
        "Мои заявки — список заявок (/myapps)"
    )
    if role == 'admin':
        base += (
            "\nАдминистраторские команды:\n"
            "/allapps — все заявки\n"
            "/setstatus <id> <статус> — изменить статус\n"
            "/setrole <id> <роль> — назначить роль"
        )
    return base

logger = logging.getLogger(__name__)


def register(bot):
    """Register bot commands for ROSFINEX."""

    @bot.message_handler(commands=['start'])
    def cmd_start(m: Message):
        """Регистрация пользователя и запрос номера телефона."""
        user_id = m.from_user.id
        name = m.from_user.full_name
        stored = db.get_user(user_id)
        if stored:
            role = stored[2]
        else:
            role = 'admin' if (user_id in ADMIN_IDS or not db.any_admins()) else 'agent'
            db.add_user(user_id, None, name, role)
        phone = stored[0] if stored else None
        if not phone:
            kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.add(KeyboardButton('📱 Отправить телефон', request_contact=True))
            bot.reply_to(m, 'Пожалуйста, поделитесь номером телефона', reply_markup=kb)
        else:
            text = f'Вы зарегистрированы как {role}\n' + _help_text(role)
            bot.reply_to(m, text, reply_markup=_main_menu())

    @bot.message_handler(content_types=['contact'])
    def contact_handler(m: Message):
        """Сохраняет отправленный контакт как телефон пользователя."""
        if not m.contact or m.contact.user_id != m.from_user.id:
            return
        db.update_user_phone(m.from_user.id, m.contact.phone_number)
        role = db.get_user_role(m.from_user.id)
        text = 'Телефон сохранён\n' + _help_text(role)
        bot.reply_to(m, text, reply_markup=_main_menu())

    @bot.message_handler(commands=['newapp'])
    @bot.message_handler(func=lambda m: m.text == 'Новая заявка')
    def cmd_newapp(m: Message):
        """Добавление новой заявки в интерактивном режиме."""
        msg = bot.reply_to(m, 'ФИО клиента?')
        _NEW_APP_DATA[m.from_user.id] = {}
        bot.register_next_step_handler(msg, _step_phone)

    def _step_phone(message: Message):
        full_name = (message.text or '').strip()
        if not full_name or full_name.startswith('/'):
            msg = bot.reply_to(message, 'Неверный формат. ФИО клиента?')
            bot.register_next_step_handler(msg, _step_phone)
            return
        data = _NEW_APP_DATA.get(message.from_user.id, {})
        data['full_name'] = full_name
        msg = bot.send_message(message.chat.id, 'Телефон клиента?')
        _NEW_APP_DATA[message.from_user.id] = data
        bot.register_next_step_handler(msg, _step_city)

    def _step_city(message: Message):
        phone = (message.text or '').strip()
        if not re.fullmatch(r'\+?\d{5,15}', phone):
            msg = bot.reply_to(message, 'Неверный формат. Телефон клиента?')
            bot.register_next_step_handler(msg, _step_city)
            return
        data = _NEW_APP_DATA.get(message.from_user.id, {})
        data['phone'] = phone
        msg = bot.send_message(message.chat.id, 'Город клиента?')
        _NEW_APP_DATA[message.from_user.id] = data
        bot.register_next_step_handler(msg, _step_interest)

    def _step_interest(message: Message):
        city = (message.text or '').strip()
        if not city:
            msg = bot.reply_to(message, 'Неверный формат. Город клиента?')
            bot.register_next_step_handler(msg, _step_interest)
            return
        data = _NEW_APP_DATA.get(message.from_user.id, {})
        data['city'] = city
        msg = bot.send_message(message.chat.id, 'Интерес клиента?')
        _NEW_APP_DATA[message.from_user.id] = data
        bot.register_next_step_handler(msg, _step_comment)

    def _step_comment(message: Message):
        interest = (message.text or '').strip()
        if not interest:
            msg = bot.reply_to(message, 'Неверный формат. Интерес клиента?')
            bot.register_next_step_handler(msg, _step_comment)
            return
        data = _NEW_APP_DATA.get(message.from_user.id, {})
        data['interest'] = interest
        msg = bot.send_message(message.chat.id, 'Комментарий?')
        _NEW_APP_DATA[message.from_user.id] = data
        bot.register_next_step_handler(msg, _finish_newapp)

    def _finish_newapp(message: Message):
        data = _NEW_APP_DATA.pop(message.from_user.id, {})
        comment = (message.text or '').strip()
        if not comment:
            msg = bot.reply_to(message, 'Неверный формат. Комментарий?')
            _NEW_APP_DATA[message.from_user.id] = data
            bot.register_next_step_handler(msg, _finish_newapp)
            return
        full_name = data.get('full_name')
        phone = data.get('phone')
        city = data.get('city')
        interest = data.get('interest')
        app_id = db.add_application(
            message.from_user.id,
            full_name,
            phone,
            city,
            interest,
            comment,
        )
        bot.send_message(message.chat.id, f'Заявка #{app_id} добавлена', reply_markup=_main_menu())

    @bot.message_handler(commands=['myapps'])
    @bot.message_handler(func=lambda m: m.text == 'Мои заявки')
    def cmd_myapps(m: Message):
        """Список заявок пользователя."""
        apps = db.get_user_applications(m.from_user.id)
        if not apps:
            return bot.reply_to(m, 'У вас нет заявок', reply_markup=_main_menu())
        lines = [f"{row[0]}: {row[1]} - {row[2]}" for row in apps]
        bot.reply_to(m, '\n'.join(lines), reply_markup=_main_menu())

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

    @bot.message_handler(commands=['setrole'])
    def cmd_setrole(m: Message):
        """Назначение роли пользователю (администратор)."""
        if m.from_user.id not in ADMIN_IDS:
            return
        parts = m.text.split(maxsplit=2)
        if len(parts) < 3:
            return bot.reply_to(m, 'Используйте: /setrole id роль')
        try:
            uid = int(parts[1])
        except ValueError:
            return bot.reply_to(m, 'id должен быть числом')
        role = parts[2].strip()
        db.update_user_role(uid, role)
        bot.reply_to(m, 'Роль обновлена')

