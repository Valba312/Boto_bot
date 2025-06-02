import logging
from db import repository as db
from keyboards import list_kb
from utils import throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    @throttling_decorator
    @bot.message_handler(commands=['f', 'filter'])
    def cmd_filter(m):
        cid = m.chat.id
        tid = m.message_thread_id

        # Просто сразу повторяем код как будто был нажат "Не выполнено"
        try:
            status_key = 'ne'
            human = 'не выполнено'
            mids = db.get_tasks_by_status(cid, tid, human)
            if not mids:
                bot.send_message(cid, "❌ Нет невыполненных задач.", message_thread_id=tid)
                return

            kb = list_kb(cid, mids, status_key, tid)
            bot.send_message(
                cid,
                f"📋 Задачи «{human}»:",
                reply_markup=kb,
                message_thread_id=tid
            )
        except Exception:
            logger.exception("Ошибка при выводе невыполненных задач")
            bot.reply_to(m, "❗ Не удалось получить задачи.", message_thread_id=tid)
