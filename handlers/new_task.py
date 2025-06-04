import logging
from telebot.apihelper import ApiTelegramException
from db import repository as db
from keyboards import action_kb
from utils import escape_html, get_author, throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    """Регистрация команды добавления новой задачи"""

    @throttling_decorator
    @bot.message_handler(commands=['t'])
    def cmd_newtask(m):
        """Создаёт новую задачу из текста после команды /t"""
        cid = m.chat.id
        tid = m.message_thread_id

        text = m.text or ''  # если message.text нет, используем пустую строку
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            return bot.reply_to(
                m,
                "❗ Неверный формат. Используйте:\n"
                "<code>/t текст задачи</code>",
                parse_mode='HTML',
                message_thread_id=tid
            )
        task_text = parts[1].strip()

        try:
            bot.delete_message(cid, m.message_id)
        except Exception:
            logger.warning("Не удалось удалить исходное сообщение", exc_info=True)

        author = get_author(m.from_user)
        esc_text = escape_html(task_text)
        esc_author = escape_html(author)

        try:
            html_text = (
                f"<b>Задача:</b> {esc_text}\n"
                f"<b>Поставил:</b> {esc_author}"
            )
            sent = bot.send_message(
                cid,
                html_text,
                parse_mode='HTML',
                message_thread_id=tid
            )
            mid = sent.message_id
        except Exception:
            logger.exception("Ошибка при отправке задачи")
            return bot.reply_to(m, "❗ Ошибка при отправке задачи.", message_thread_id=tid)

        try:
            kb = action_kb(tid, mid)
            bot.edit_message_reply_markup(cid, mid, reply_markup=kb)
        except Exception:
            logger.warning("Не удалось прикрепить клавиатуру", exc_info=True)

        try:
            db.add_task(cid, tid, mid, author, task_text, 'не выполнено', None)
        except Exception:
            logger.exception("Ошибка при сохранении задачи в БД")
            bot.send_message(cid, "❗ Не удалось сохранить задачу.", message_thread_id=tid)


