import logging
from telebot.types import CallbackQuery
from telebot.apihelper import ApiTelegramException
from db import repository as db
from keyboards import list_kb
from utils import throttling_decorator

logger = logging.getLogger(__name__)

# Словарь, чтобы преобразовать status_key ('ne', 'accepted') в текст для БД:
STATUS_HUMAN = {
    'ne': 'не выполнено',
    'accepted': 'принято'
}

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

        # 1) Читаем задачу из БД, чтобы получить текст
        try:
            row = db.get_task_by_id(cid, tid, mid)
            if not row:
                # Вдруг в БД уже нет такой записи?
                raise LookupError("Задача не найдена в БД")
            _, text, _, _ = row
        except Exception:
            logger.exception("Ошибка чтения задачи по message_id")
            return bot.answer_callback_query(cb.id, "❗ Не удалось найти задачу", show_alert=True)

        # 2) Выбираем префикс по статусу (на будущее — если понадобится)
        prefix = {
            'ne': '❌ Не выполненная задача',
            'accepted': '✅ Принятая задача'
        }.get(status_key, '📌 Задача')

        # 3) Пытаемся отправить reply к тому самому сообщению mid
        try:
            bot.send_message(
                cid,
                f"{prefix}: {text}",
                reply_to_message_id=mid,
                message_thread_id=tid
            )
        except ApiTelegramException as e:
            # Если Telegram отвечает “message to be replied not found” → исходное сообщение удалено
            desc = getattr(e, 'result_json', {}).get('description', '') or ''
            if e.error_code == 400 and 'message to be replied not found' in desc:
                # ---- Удаляем задачу из БД ----
                try:
                    db.delete_task(cid, tid, mid)
                    logger.info(f"callback_task: удалена битая задача mid={mid}, chat={cid}, thread={tid}")
                except Exception:
                    logger.exception("callback_task: ошибка при delete_task")

                # ---- Обновляем (перерисовываем) клавиатуру фильтра ----
                try:
                    # Нужный статус в БД (человекопонятный):
                    human_status = STATUS_HUMAN.get(status_key, None)
                    if human_status is not None:
                        # Берём все оставшиеся message_id для этого статуса
                        remaining_mids = db.get_tasks_by_status(cid, tid, human_status)
                        # Генерируем новую inline‐клавиатуру
                        new_kb = list_kb(cid, remaining_mids, status_key, tid)
                        # Редактируем старую клавиатуру (той же кнопкой «task|...»):
                        bot.edit_message_reply_markup(
                            chat_id=cid,
                            message_id=cb.message.message_id,
                            reply_markup=new_kb
                        )
                    else:
                        # Если по каким-то причинам status_key неизвестен, просто уберём клавиатуру:
                        bot.edit_message_reply_markup(
                            chat_id=cid,
                            message_id=cb.message.message_id,
                            reply_markup=None
                        )
                except Exception:
                    logger.exception("callback_task: не удалось обновить клавиатуру после удаления задачи")

                # ---- Сообщаем пользователю в alert, что “битая” задача убрана ----
                return bot.answer_callback_query(
                    cb.id,
                    "❗ Исходное сообщение с задачей удалено, задача убрана из списка.",
                    show_alert=True
                )
            else:
                # Другая ошибка отправки (не “message not found”)
                logger.exception("Ошибка отправки сообщения с задачей")
                return bot.answer_callback_query(
                    cb.id,
                    "❗ Ошибка при отправке задачи.",
                    show_alert=True
                )

        # 4) Если reply отправился успешно, просто закрываем callback без алерта
        try:
            bot.answer_callback_query(cb.id)
        except Exception:
            logger.exception("Ошибка в answer_callback_query")
