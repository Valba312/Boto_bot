import logging
from db import repository as db
from keyboards import list_kb
from utils import throttling_decorator
from telebot.apihelper import ApiTelegramException

logger = logging.getLogger(__name__)

def register(bot):
    @throttling_decorator
    @bot.message_handler(commands=['f', 'filter'])
    def cmd_filter(m):
        cid = m.chat.id
        tid = m.message_thread_id

        try:
            status_key = 'ne'
            human = 'не выполнено'
            mids = db.get_tasks(cid, tid, human)

            if not mids:
                bot.send_message(cid, "❌ Нет невыполненных задач.", message_thread_id=tid)
                return

            try:
                kb = list_kb(cid, mids, status_key, tid)
                bot.send_message(
                    cid,
                    f"📋 Задачи «{human}»:",
                    reply_markup=kb,
                    message_thread_id=tid
                )
            except ApiTelegramException as e:
                if e.error_code == 429:
                    logger.warning("Rate limit на отправку списка задач")
                else:
                    logger.exception("Ошибка при отправке списка задач")

        except Exception:
            logger.exception("Ошибка при выводе невыполненных задач")
            try:
                bot.reply_to(m, "❗ Не удалось получить задачи.", message_thread_id=tid)
            except ApiTelegramException as e:
                if e.error_code == 429:
                    logger.warning("❗ reply_to попал под rate limit")
                else:
                    logger.exception("Ошибка при reply_to")
