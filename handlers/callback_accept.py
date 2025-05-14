from db import repository as db
from utils import get_author, escape_html
import logging
from utils import throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    @throttling_decorator
    @bot.callback_query_handler(lambda cb: cb.data.startswith('accept|'))
    def cb_accept(cb):
        try:
            _, tid_s, mid_s = cb.data.split('|', 2)
            tid = None if tid_s == 'None' else int(tid_s)
            mid = int(mid_s)
            cid = cb.message.chat.id
        except Exception:
            return bot.answer_callback_query(cb.id, "❗ Неверные данные кнопки", show_alert=True)

        taker = get_author(cb.from_user)

        try:
            author, text, _, _ = db.get_task_by_id(cid, tid, mid)
        except Exception:
            logger.exception("Ошибка чтения задачи")
            return bot.answer_callback_query(cb.id, "❗ Не удалось получить задачу", show_alert=True)

        try:
            db.update_task_status(cid, tid, mid, 'принято', taker)
        except Exception:
            logger.exception("Ошибка обновления статуса в БД")

        new_text = (
            f"✅ <s><b>Задача:</b> {escape_html(text)}</s>\n"
            f"<b>Поставил:</b> {escape_html(author)}\n"
            f"<b>Принял:</b> {escape_html(taker)}"
        )

        try:
            bot.edit_message_text(new_text, cid, mid, parse_mode='HTML')
        except Exception:
            logger.warning("Ошибка редактирования текста задачи", exc_info=True)

        bot.answer_callback_query(cb.id, "✅ Задача принята")
