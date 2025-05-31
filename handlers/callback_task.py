import logging
from telebot.types import CallbackQuery
from telebot.apihelper import ApiTelegramException
from db import repository as db
from utils import parse_callback, throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    @throttling_decorator
    @bot.callback_query_handler(func=lambda c: c.data.startswith("task|"))
    def task_callback(cb: CallbackQuery):
        cid = cb.message.chat.id
        tid = cb.message.message_thread_id
        data = cb.data

        _, mid, status, _ = parse_callback(data)

        try:
            # Просто отправляем reply к исходному сообщению
            bot.send_message(
                cid,
                "🔗 Задача 👇",
                reply_to_message_id=int(mid),
                message_thread_id=tid
            )
            bot.answer_callback_query(cb.id, "Задача открыта 👀")
        except ApiTelegramException as e:
            if "message to reply not found" in str(e):
                db.delete_task_by_message_id(mid)
                bot.answer_callback_query(cb.id, "❌ Задача больше не существует", show_alert=True)
            elif e.error_code == 429:
                logger.warning(f"[RATE LIMIT] {e}")
                bot.answer_callback_query(cb.id, "Слишком много запросов, попробуйте позже", show_alert=True)
            else:
                logger.warning(f"[API ERROR] message_id={mid} ➜ {e}")
                bot.answer_callback_query(cb.id, "⚠ Не удалось открыть задачу", show_alert=True)
        except Exception as e:
            logger.exception("Ошибка при обработке task callback")
            bot.answer_callback_query(cb.id, "⚠ Не удалось открыть задачу", show_alert=True)
