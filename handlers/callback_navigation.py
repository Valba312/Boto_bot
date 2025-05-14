import logging
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import repository as db
import re
from keyboards import status_kb, list_kb
from utils import throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    BATCH_SIZE = 4           # Количество сообщений в батче
    SHORT_SLEEP = 0.35       # Задержка между сообщениями
    LONG_SLEEP = 0.5         # Задержка между батчами
    MAX_SPAM_SLEEP = 5  # 5 секунд максимум

    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

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

        # Удаляем только кнопку «Прислать все»
        try:
            kb = list_kb(cid, mids, status_key, tid, show_send_all=False)
            bot.edit_message_reply_markup(
                chat_id=cid,
                message_id=cb.message.message_id,
                reply_markup=kb
            )
        except Exception:
            logger.warning("Ошибка обновления клавиатуры в send_all", exc_info=True)

        sent = 0
        for batch in chunks(mids, BATCH_SIZE):
            for mid in batch:
                try:
                    _, text, _, _ = db.get_task_by_id(cid, tid, mid)
                    msg = f"❌ Не выполнено: {text}" if status_key == 'ne' else f"✅ Принято: {text}"
                    bot.send_message(cid, msg, reply_to_message_id=mid, message_thread_id=tid)
                    sent += 1
                    time.sleep(SHORT_SLEEP)
                except Exception as e:
                    desc = getattr(e, 'result_json', {}).get('description', '')
                    # Проверка лимита
                    if hasattr(e, 'error_code') and e.error_code == 429:
                        retry_after = 1
                        m = re.search(r'retry after (\d+)', desc)
                        if m:
                            retry_after = int(m.group(1))
                        if retry_after > MAX_SPAM_SLEEP:
                            bot.send_message(cid, "❗ Превышено количество запросов, пожалуйста подождите.", message_thread_id=tid)
                            logger.warning(f"Лимит превышен, требуется спать {retry_after}s — отмена send_all")
                            bot.answer_callback_query(cb.id, f"📨 Отправлено: {sent}")
                            return
                        else:
                            time.sleep(retry_after)
                            try:
                                bot.send_message(cid, msg, reply_to_message_id=mid, message_thread_id=tid)
                                sent += 1
                            except Exception as e2:
                                logging.warning(f"Ошибка при повторной попытке отправить задачу {mid}: {e2}")
                    else:
                        logging.warning(f"Ошибка при отправке задачи {mid}: {e}")
            # Пауза между батчами (кроме последнего)
            if batch != mids[-BATCH_SIZE:]:
                time.sleep(LONG_SLEEP)

        bot.answer_callback_query(cb.id, f"📨 Отправлено: {sent}")

    @throttling_decorator
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