import logging
from keyboards import status_kb
from utils import throttling_decorator

logger = logging.getLogger(__name__)

def register(bot):
    @throttling_decorator
    @bot.message_handler(commands=['filter'])
    def cmd_filter(m):
        cid = m.chat.id
        tid = m.message_thread_id

        try:
            kb = status_kb(tid)
            bot.send_message(
                cid,
                "Выберите статус:",
                reply_markup=kb,
                message_thread_id=tid
            )
        except Exception:
            logger.exception("Ошибка при отправке меню фильтра")
            bot.reply_to(m, "❗ Не удалось показать меню фильтра.", message_thread_id=tid)
