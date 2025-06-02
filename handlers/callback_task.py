import logging
from telebot.types import CallbackQuery
from telebot.apihelper import ApiTelegramException
from db import repository as db
from utils import throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    @throttling_decorator
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

        # Берём строку задачи из БД
        try:
            row = db.get_task_by_id(cid, tid, mid)
            if not row:
                raise LookupError("Задача не найдена в БД")
            _, text, _, _ = row
        except Exception:
            logger.exception("Ошибка чтения задачи по message_id")
            return bot.answer_callback_query(cb.id, "❗ Не удалось найти задачу", show_alert=True)

        # Префикс зависит от статуса
        prefix = {
            'ne': '❌ Не выполненная задача',
            'accepted': '✅ Принятая задача'
        }.get(status_key, '📌 Задача')

        # Пытаемся отправить ответ (reply) ссылкой на исходное сообщение.
        # Если исходного сообщения уже нет, поймаем ApiTelegramException.
        try:
            bot.send_message(
                cid,
                f"{prefix}: {text}",
                reply_to_message_id=mid,
                message_thread_id=tid
            )
        except ApiTelegramException as e:
            # Telegram возвращает error_code=400 и описание вида "Bad Request: message to be replied not found"
            desc = getattr(e, 'result_json', {}).get('description', '') or ''
            # Сравниваем по подстроке "reply message not found"
            if e.error_code == 400 and 'message to be replied not found' in desc:
                # Исходного сообщения нет — удаляем таск из БД и сообщаем пользователю
                try:
                    db.delete_task(cid, tid, mid)
                    logger.info(f"callback_task: удалена битая задача mid={mid} в chat={cid}, thread={tid}")
                except Exception:
                    logger.exception("callback_task: ошибка при delete_task")
                return bot.answer_callback_query(
                    cb.id,
                    "❗ Исходное сообщение с задачей удалено, задача убрана из списка.",
                    show_alert=True
                )
            else:
                # Если другая ошибка, просто логируем и сообщаем generic-сообщение
                logger.exception("Ошибка отправки сообщения с задачей")
                return bot.answer_callback_query(
                    cb.id,
                    "❗ Ошибка при отправке задачи.",
                    show_alert=True
                )

        # Если отправка reply прошла успешно, просто закрываем callback
        try:
            bot.answer_callback_query(cb.id)
        except Exception:
            logger.exception("Ошибка в answer_callback_query")