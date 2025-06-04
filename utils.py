import html
import time
import logging
from telebot.apihelper import ApiTelegramException
from config import ADMIN_IDS

def escape_html(text: str) -> str:
    """Безопасный HTML-escape для текста"""
    return html.escape(text)


def is_admin(user_id: int) -> bool:
    """Проверяет, есть ли идентификатор пользователя в списке ADMIN_IDS."""
    return user_id in ADMIN_IDS

def get_author(user) -> str:
    """Безопасно формирует имя автора задачи из объекта user"""
    try:
        if not user:
            return "<unknown>"
        username = getattr(user, "username", None)
        if username:
            return f"@{username}"
        first = getattr(user, "first_name", "")
        last = getattr(user, "last_name", "")
        full_name = f"{first} {last}".strip()
        if full_name:
            return full_name
        uid = getattr(user, "id", None)
        if uid:
            return f"Пользователь ({uid})"
        return "<unknown>"
    except Exception as e:
        print(f"[get_author] Ошибка: {e}, user={user}")
        return "<unknown>"

def throttling_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            time.sleep(0.3)
            return func(*args, **kwargs)
        except ApiTelegramException as e:
            desc = getattr(e, 'result_json', {}).get('description', '')
            if e.error_code == 429 or 'Too Many Requests' in desc or 'retry after' in desc:
                logging.warning("429: Приостанавливаем работу на 1.5 секунды")
                time.sleep(1.5)
                try:
                    return func(*args, **kwargs)
                except ApiTelegramException as e2:
                    desc2 = getattr(e2, 'result_json', {}).get('description', '')
                    if e2.error_code == 429 or 'Too Many Requests' in desc2 or 'retry after' in desc2:
                        message = None
                        # пробуем достать message или cb (для колбэка)
                        for arg in args:
                            if hasattr(arg, 'chat') and hasattr(arg, 'message_id'):
                                message = arg
                                break
                        if message is not None:
                            bot = kwargs.get('bot') or args[0].bot
                            bot.send_message(message.chat.id, "Превышен лимит, пожалуйста подождите")
                        else:
                            logging.warning("Не удалось отправить сообщение о лимите")
                        return
                    raise
            raise
    return wrapper

