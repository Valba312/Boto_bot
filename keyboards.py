from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import repository as db

def action_kb(thread_id, message_id=None):
    """Кнопка «Принято» (accept|<thread_id>|<message_id>)"""
    kb = InlineKeyboardMarkup()
    cb = f"accept|{thread_id}|{message_id}"
    kb.add(InlineKeyboardButton("✅ Взять в работу", callback_data=cb))
    return kb

def status_kb(thread_id):
    """Меню выбора статуса (status|ne|<thread_id>)"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Не выполнено",  callback_data=f"status|ne|{thread_id}"))
    kb.add(InlineKeyboardButton("Принято",        callback_data=f"status|accepted|{thread_id}"))
    return kb

def list_kb(chat_id, message_ids, status_key, thread_id):
    """Список задач по статусу"""
    human = {'ne': 'не выполнено', 'accepted': 'принято'}[status_key]
    kb = InlineKeyboardMarkup()

    for mid in message_ids:
        try:
            author, text, _, _ = db.get_task_by_id(chat_id, thread_id, mid)
        except Exception:
            text = '<ошибка>'
        label = text if len(text) < 20 else text[:20] + '…'
        cb = f"task|{mid}|{status_key}|{thread_id}"
        kb.add(InlineKeyboardButton(label, callback_data=cb))

    kb.add(InlineKeyboardButton("📨 Прислать все", callback_data=f"send_all|{status_key}|{thread_id}"))
    kb.add(InlineKeyboardButton("◀ К статусам", callback_data=f"back_status|{thread_id}"))
    return kb

def details_kb(status_key, thread_id):
    """Кнопка «Назад к списку задач»"""
    cb = f"back_list|{status_key}|{thread_id}"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("◀ К списку", callback_data=cb))
    return kb
