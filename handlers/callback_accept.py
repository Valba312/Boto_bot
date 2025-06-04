import logging
from telebot.types import CallbackQuery
from telebot.apihelper import ApiTelegramException
from db import repository as db
from utils import get_author, escape_html, throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    """Регистрирует колбэк для принятия задачи исполнителем"""

    @throttling_decorator
    @bot.callback_query_handler(lambda cb: cb.data.startswith('accept|'))
    def cb_accept(cb: CallbackQuery):
        """Обрабатывает нажатие кнопки «Взять в работу»"""
        try:
            # Разбор callback_data: accept|<thread_id>|<message_id>
            _, tid_s, mid_s = cb.data.split('|', 2)
            tid = None if tid_s == 'None' else int(tid_s)
            mid = int(mid_s)
            cid = cb.message.chat.id
        except Exception:
            return bot.answer_callback_query(cb.id, "❗ Неверные данные кнопки", show_alert=True)

        taker = get_author(cb.from_user)

        # Получаем параметры задачи из БД (автор и текст)
        try:
            author, text, _, _ = db.get_task_by_id(cid, tid, mid)
            if author is None:
                raise LookupError("Задача не найдена")
        except Exception:
            logger.exception("callback_accept: ошибка чтения задачи из БД")
            return bot.answer_callback_query(cb.id, "❗ Не удалось получить задачу", show_alert=True)

        # Сохраняем в БД, что задачу принял taker
        try:
            db.update_task_status(cid, tid, mid, 'принято', taker)
        except Exception:
            logger.exception("callback_accept: ошибка update_task_status")

        # Новое форматирование текста задачи (зачёркивание + кто принял)
        new_text = (
            f"✅ <s><b>Задача:</b> {escape_html(text)}</s>\n"
            f"<b>Поставил:</b> {escape_html(author)}\n"
            f"<b>Принял:</b> {escape_html(taker)}"
        )

        # Пытаемся отредактировать исходное сообщение. Если его уже нет, удаляем таск из БД
        try:
            bot.edit_message_text(new_text, cid, mid, parse_mode='HTML')
        except ApiTelegramException as e:
            desc = getattr(e, 'result_json', {}).get('description', '') or ''
            # Telegram выдаёт "Bad Request: message to be edited not found" или похожее
            if e.error_code == 400 and ('message to be edited not found' in desc or 'message to edit not found' in desc):
                try:
                    db.delete_task(cid, tid, mid)
                    logger.info(f"callback_accept: удалена битая задача (edit not found), mid={mid}, chat={cid}, thread={tid}")
                except Exception:
                    logger.exception("callback_accept: ошибка при delete_task")
                return bot.answer_callback_query(
                    cb.id,
                    "❗ Сообщение с задачей удалено, задача убрана из списка.",
                    show_alert=True
                )
            else:
                logger.exception("callback_accept: ошибка редактирования текста задачи")
                return bot.answer_callback_query(cb.id, "❗ Не удалось обновить задачу", show_alert=True)

        # Если всё успешно отредактировали — просто отвечаем без show_alert
        try:
            bot.answer_callback_query(cb.id, "✅ Задача принята")
        except Exception:
            logger.exception("callback_accept: ошибка в answer_callback_query")

