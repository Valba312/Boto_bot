import logging
from telebot.types import CallbackQuery
from db import repository as db

logger = logging.getLogger(__name__)

def register(bot):

    @bot.callback_query_handler(lambda cb: cb.data.startswith('task|'))
    def cb_task(cb: CallbackQuery):
        try:
            # Разбор callback_data: task|<message_id>|<status_key>|<thread_id>
            _, mid_s, status_key, tid_s = cb.data.split('|', 3)
            mid = int(mid_s)
            tid = None if tid_s == 'None' else int(tid_s)
            cid = cb.message.chat.id
        except Exception:
            logger.exception("Ошибка разбора callback task")
            return bot.answer_callback_query(cb.id, "❗ Ошибка кнопки", show_alert=True)

        # Получаем текст задачи из базы
        try:
            row = db.get_task_by_id(cid, tid, mid)
            if not row:
                raise LookupError("Задача не найдена")
            _, text, _, _ = row
        except Exception:
            logger.exception("Ошибка чтения задачи по message_id")
            return bot.answer_callback_query(cb.id, "❗ Не удалось найти задачу", show_alert=True)

        # Выбираем префикс по статусу
        prefix = {
            'ne': '❌ Не выполненная задача',
            'accepted': '✅ Принятая задача'
        }.get(status_key, '📌 Задача')

        # Отправляем сообщение с reply_to
        try:
            bot.send_message(
                cid,
                f"{prefix}: {text}",
                reply_to_message_id=mid,
                message_thread_id=tid
            )
        except Exception:
            logger.exception("Ошибка отправки сообщения с задачей")

        # Закрываем callback
        try:
            bot.answer_callback_query(cb.id)
        except Exception:
            logger.exception("Ошибка в answer_callback_query")
