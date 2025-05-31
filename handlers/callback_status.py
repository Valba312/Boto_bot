from db import repository as db
from keyboards import list_kb
import logging
from utils import throttling_decorator

logger = logging.getLogger(__name__)

# callback_status.py

def register(bot):
    @bot.callback_query_handler(lambda cb: cb.data.startswith('status|'))
    def cb_status(cb):
        # Просто сообщаем, что меню статусов отключено
        bot.answer_callback_query(cb.id, "Меню статусов отключено.", show_alert=True)

