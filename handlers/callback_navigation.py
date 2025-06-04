import logging
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import repository as db
import re
from keyboards import status_kb, list_kb
from utils import throttling_decorator

logger = logging.getLogger(__name__)

# callback_navigation.py

def register(bot):
    @bot.callback_query_handler(lambda cb: cb.data.startswith('send_all|'))
    def cb_send_all(cb):
        bot.answer_callback_query(cb.id, "Массовая отправка задач отключена.", show_alert=True)

    @bot.callback_query_handler(lambda cb: cb.data.startswith('back_status|'))
    def cb_back_status(cb):
        bot.answer_callback_query(cb.id, "Меню статусов отключено.", show_alert=True)
