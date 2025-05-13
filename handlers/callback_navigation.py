import logging
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import repository as db
from keyboards import status_kb, list_kb

logger = logging.getLogger(__name__)

def register(bot):

    @bot.callback_query_handler(lambda cb: cb.data.startswith('send_all|'))
    def cb_send_all(cb):
        try:
            _, status_key, tid_s = cb.data.split('|', 2)
            tid = None if tid_s == 'None' else int(tid_s)
            cid = cb.message.chat.id
        except Exception:
            logger.exception("Ошибка разбора send_all")
            return bot.answer_callback_query(cb.id, "❗ Ошибка формата", show_alert=True)

        # Получение задач
        try:
            human = {'ne': 'не выполнено', 'accepted': 'принято'}[status_key]
            mids = db.get_tasks_by_status(cid, tid, human)
        except Exception:
            logger.exception("Ошибка получения задач")
            return bot.answer_callback_query(cb.id, "❗ Не удалось загрузить задачи", show_alert=True)

        if not mids:
            return bot.answer_callback_query(cb.id, "Нет задач для отправки")

        sent = 0
        for mid in mids:
            try:
                _, text, _, _ = db.get_task_by_id(cid, tid, mid)
                msg = f"❌ Не выполнено: {text}" if status_key == 'ne' else f"✅ Принято: {text}"
                bot.send_message(cid, msg, reply_to_message_id=mid, message_thread_id=tid)
                sent += 1
            except Exception:
                logger.warning(f"Ошибка при отправке задачи {mid}", exc_info=True)

        # Обновление клавиатуры: удаляем «Прислать все»
        try:
            kb = list_kb(cid, mids, status_key, tid)
            bot.edit_message_reply_markup(
                chat_id=cid,
                message_id=cb.message.message_id,
                reply_markup=kb
            )
        except Exception:
            logger.warning("Ошибка обновления клавиатуры после send_all", exc_info=True)

        bot.answer_callback_query(cb.id, f"📨 Отправлено: {sent}")

    @bot.callback_query_handler(lambda cb: cb.data.startswith('back_status|'))
    def cb_back_status(cb):
        try:
            _, tid_s = cb.data.split('|', 1)
            tid = None if tid_s == 'None' else int(tid_s)
            cid = cb.message.chat.id
        except Exception:
            logger.exception("Ошибка разбора back_status")
            return bot.answer_callback_query(cb.id, "❗ Ошибка кнопки", show_alert=True)

        try:
            kb = status_kb(tid)
            bot.edit_message_text(
                "Выберите статус:",
                chat_id=cid,
                message_id=cb.message.message_id,
                reply_markup=kb
            )
        except Exception:
            logger.exception("Ошибка при возврате к статусам")
        finally:
            bot.answer_callback_query(cb.id)