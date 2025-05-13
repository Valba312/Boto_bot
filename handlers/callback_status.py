from db import repository as db
from keyboards import list_kb
import logging

logger = logging.getLogger(__name__)

def register(bot):

    @bot.callback_query_handler(lambda cb: cb.data.startswith('status|'))
    def cb_status(cb):
        try:
            _, status_key, tid_s = cb.data.split('|', 2)
            tid = None if tid_s == 'None' else int(tid_s)
            cid = cb.message.chat.id
            human = {'ne': 'не выполнено', 'accepted': 'принято'}[status_key]
        except Exception:
            return bot.answer_callback_query(cb.id, "❗ Ошибка данных", show_alert=True)

        try:
            mids = db.get_tasks_by_status(cid, tid, human)
        except Exception:
            logger.exception("Ошибка получения задач")
            return bot.send_message(cid, "❗ Не удалось получить задачи.", message_thread_id=tid)

        if not mids:
            from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("◀ К статусам", callback_data=f"back_status|{tid}")
            )
            return bot.edit_message_text(f"❌ Нет задач «{human}».", cid, cb.message.message_id, reply_markup=kb)

        kb = list_kb(cid, mids, status_key, tid)
        bot.edit_message_text(f"📋 Задачи «{human}»:",
                              cid,
                              cb.message.message_id,
                              reply_markup=kb)
        bot.answer_callback_query(cb.id)
