import time
import logging
import html
import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlite3 import DatabaseError
import db

TOKEN = '7909570032:AAFppvVBCGt80n9urHgmD4u0qRAvlMKW8a8'
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Создаем таблицы при старте
db.create_tables()

# Состояния для /newtask
user_states = {}

# ─── КЛАВИАТУРЫ ─────────────────────────────────────────────────────────────────

def action_kb(tid, mid=None):
    """
    Кнопка «Принято» для только что созданной задачи.
    mid передаем, чтобы потом распознать, что приняли именно это сообщение.
    """
    kb = InlineKeyboardMarkup()
    # формат callback: accept|<thread_id>|<message_id>
    cb = f"accept|{tid}|{mid}"
    kb.add(InlineKeyboardButton("Принято", callback_data=cb))
    return kb

def status_kb(tid):
    """
    Меню выбора статуса. 
    callback: status|<status_key>|<thread_id>
    """
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Не выполнено",  callback_data=f"status|ne|{tid}"))
    kb.add(InlineKeyboardButton("Принято",        callback_data=f"status|accepted|{tid}"))
    return kb

def list_kb(cid, mids, status_key, tid):
    """
    cid        — chat.id
    mids       — список message_id
    status_key — 'ne' или 'accepted'
    tid        — thread_id (или None)
    """
    human = {'ne':'не выполнено','accepted':'принято'}[status_key]
    kb = InlineKeyboardMarkup()
    for mid in mids:
        try:
            author, text, _, taker = db.get_task_by_id(cid, tid, mid)
        except Exception:
            author, text, taker = '', '<ошибка чтения>', None
        label = text if len(text)<20 else text[:20]+'…'
        cb    = f"task|{mid}|{status_key}|{tid}"
        kb.add(InlineKeyboardButton(label, callback_data=cb))

    kb.add(InlineKeyboardButton("📨 Прислать все",
                callback_data=f"send_all|{status_key}|{tid}"))
    kb.add(InlineKeyboardButton("◀ К статусам",
                callback_data=f"back_status|{tid}"))
    return kb

def details_kb(status_key, tid):
    """
    Кнопка «Назад к списку» из деталей.
    callback: back_list|<status_key>|<thread_id>
    """
    cb = f"back_list|{status_key}|{tid}"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("◀ К списку", callback_data=cb))
    return kb

# ─── /t ─────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['t'])
def cmd_newtask(m):
    cid = m.chat.id
    tid = m.message_thread_id

    # 1) Чтение текста команды
    try:
        text = m.text
    except AttributeError:
        logger.exception("m.text is missing or invalid")
        return bot.reply_to(
            m,
            "❗ Не удалось прочитать текст команды.",
            message_thread_id=tid
        )

    # 2) Разбор формата
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return bot.reply_to(
            m,
            "❗ Неверный формат. Используйте:\n"
            "<code>/t текст задачи</code>",
            parse_mode='HTML',
            message_thread_id=tid
        )
    task_text = parts[1].strip()

    # 3) Удаление исходного сообщения
    try:
        bot.delete_message(cid, m.message_id)
    except ApiTelegramException:
        logger.warning("Не удалось удалить исходное сообщение", exc_info=True)
    except Exception:
        logger.exception("Unexpected error during delete_message")

    # 4) Формирование автора
    try:
        user = m.from_user
        author = f"@{user.username}" if user.username else user.first_name or str(user.id)
    except AttributeError:
        logger.warning("Missing m.from_user data", exc_info=True)
        author = "<unknown>"

    # 5) HTML-экранирование
    try:
        esc_text   = html.escape(task_text)
        esc_author = html.escape(author)
    except TypeError:
        logger.exception("html.escape got non-string")
        esc_text   = str(task_text)
        esc_author = str(author)

    # 6) Отправка сообщения с задачей
    try:
        html_text = (
            f"<b>Задача:</b> {esc_text}\n"
            f"<b>Поставил:</b> {esc_author}\n"
            f"<b>Статус:</b> ❗ Не выполнено"
        )
        sent = bot.send_message(
            cid,
            html_text,
            parse_mode='HTML',
            message_thread_id=tid
        )
        mid = sent.message_id
    except ApiTelegramException:
        logger.exception("ApiTelegramException on send_message")
        return bot.reply_to(
            m,
            "❗ Не удалось отправить задачу. Проверьте права бота.",
            message_thread_id=tid
        )
    except Exception:
        logger.exception("Unexpected error on send_message")
        return bot.reply_to(
            m,
            "❗ Ошибка при отправке задачи. Попробуйте позже.",
            message_thread_id=tid
        )

    # 7) Прикрепление кнопки «Взять в работу»
    try:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Взять в работу", callback_data=f"accept|{tid}|{mid}"))
        bot.edit_message_reply_markup(cid, mid, reply_markup=kb)
    except ApiTelegramException:
        logger.warning("Не удалось прикрепить клавиатуру", exc_info=True)
    except Exception:
        logger.exception("Unexpected error on edit_message_reply_markup")

    # 8) Сохранение задачи в БД — OperationalError
    try:
        db.add_task(cid, tid, mid, author, task_text, 'не выполнено', None)
    except db.OperationalError:
        logger.exception("OperationalError on DB insert")
        bot.send_message(
            cid,
            "❗ Проблема с базой данных. Попробуйте позже.",
            message_thread_id=tid
        )
        return
    # 9) Сохранение задачи в БД — DatabaseError
    except db.DatabaseError:
        logger.exception("DatabaseError on DB insert")
        bot.send_message(
            cid,
            "❗ Внутренняя ошибка базы данных.",
            message_thread_id=tid
        )
        return
    # 10) Прочие ошибки БД
    except Exception:
        logger.exception("Unknown error on DB insert")
        bot.send_message(
            cid,
            "❗ Не удалось сохранить задачу. Повторите попытку.",
            message_thread_id=tid
        )
        return

    # 11) Общая «ловушка» на случай любых других непредвиденных исключений
    # (например, если выше что-то пропустили)
    try:
        pass  # здесь уже всё успешно сделано
    except Exception:
        logger.exception("Critical unexpected error in /t handler")
        bot.reply_to(
            m,
            "❗ Произошла непредвиденная ошибка при создании задачи. Попробуйте позже.",
            message_thread_id=tid
        )


# ─── «Принято» ─────────────────────────────────────────────────────────────────

@bot.callback_query_handler(lambda cb: cb.data.startswith('accept|'))
def cb_accept(cb):
    # разбираем accept|<thread_id>|<message_id>
    try:
        _, tid_s, mid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        mid = int(mid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id, "Ошибка формата данных", show_alert=True)

    user = cb.from_user
    taker = f"@{user.username}" if user.username else user.first_name or str(user.id)

    try:
        author, text, _, _ = db.get_task_by_id(cid, tid, mid)
    except Exception:
        logger.exception("Ошибка БД при чтении задачи для принятия")
        return bot.answer_callback_query(cb.id, "❗ Не удалось прочесть задачу", show_alert=True)

    # Обновляем статус в БД
    try:
        db.update_task_status(cid, tid, mid, 'принято', taker)
    except Exception:
        logger.exception("Ошибка БД при обновлении статуса")

    # Экранируем через html.escape
    text_esc   = html.escape(text)
    author_esc = html.escape(author)
    taker_esc  = html.escape(taker)

    # Строим зачёркнутый HTML
    new_html = (
    f"<s><b>Задача:</b> {text_esc}</s>\n\n"
    f"<b>Принял:</b> {taker_esc}\n"
    f"<b>Статус:</b> ✅ Принято"
    )

    # Кнопка «Принято»
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Принято", callback_data="noop"))

    try:
        bot.edit_message_text(
            new_html,
            chat_id=cid,
            message_id=mid,
            parse_mode='HTML',
            reply_markup=None
        )
    except ApiTelegramException:
        logger.exception("Не удалось обновить сообщение после принятия")

    bot.answer_callback_query(cb.id, "✅ Задача помечена как принята")

# ─── /filter ───────────────────────────────────────────────────────────────────

@bot.message_handler(commands=['filter'])
def cmd_filter(m):
    cid = m.chat.id
    tid = m.message_thread_id
    try:
        kb = status_kb(tid)
        bot.send_message(cid, "Выберите статус:", reply_markup=kb, message_thread_id=tid)
    except ApiTelegramException:
        logger.exception("Ошибка API при выводе фильтра")
        bot.reply_to(m, "❗ Не удалось показать меню фильтра.")

# ─── «Статус → список» ─────────────────────────────────────────────────────────

# ——— 1) Статус → список задач ————————————————————————————————————————————
@bot.callback_query_handler(lambda cb: cb.data.startswith('status|'))
def cb_status(cb):
    try:
        # cb.data == "status|<status_key>|<thread_id>"
        _, status_key, tid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        # если вдруг формат не тот — просто тихо выходим
        return bot.answer_callback_query(cb.id, text="Ошибка формата", show_alert=True)

    human = {'ne':'не выполнено', 'accepted':'принято'}[status_key]

    # Получаем список message_id из БД
    try:
        mids = db.get_tasks_by_status(cid, tid, human)
    except DatabaseError:
        logger.exception("DB error in cb_status")
        return bot.send_message(cid,
            "❗ Не удалось получить задачи. Повторите попытку позже.",
            message_thread_id=tid)

    if not mids:
        # Если пусто — кнопка «◀ К статусам»
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("◀ К статусам", callback_data=f"back_status|{tid}")
        )
        bot.edit_message_text(f"❌ Нет задач «{human}».",
                              cid, cb.message.message_id,
                              reply_markup=kb)
    else:
        # Здесь ключевая правка: передаём в list_kb текущий cid!
        kb = list_kb(cid, mids, status_key, tid)
        bot.edit_message_text(f"📋 Задачи «{human}»:",
                              cid, cb.message.message_id,
                              reply_markup=kb)

    bot.answer_callback_query(cb.id, show_alert=False)

# ─── «Назад к статусам» ────────────────────────────────────────────────────────

@bot.callback_query_handler(lambda cb: cb.data.startswith('back_status|'))
def cb_back_status(cb):
    try:
        _, tid_s = cb.data.split('|',1)
        tid = None if tid_s=='None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id)

    try:
        kb = status_kb(tid)
        bot.edit_message_text("Выберите статус:", cid,
                              cb.message.message_id,
                              reply_markup=kb)
    except ApiTelegramException:
        logger.exception("Ошибка API при возврате к статусам")
    finally:
        bot.answer_callback_query(cb.id)

# ─── «Выбор задачи → детали» ───────────────────────────────────────────────────

@bot.callback_query_handler(lambda cb: cb.data.startswith('task|'))
def cb_task(cb):
    # формат task|<mid>|<status_key>|<thread_id>
    try:
        _, mid_s, status_key, tid_s = cb.data.split('|',3)
        mid = int(mid_s)
        tid = None if tid_s=='None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id, text="Ошибка данных", show_alert=True)

    human = {'ne':'не выполнено','accepted':'принято'}[status_key]
    try:
        author, text, _, taker = db.get_task_by_id(cid, tid, mid)
    except DatabaseError:
        logger.exception("Ошибка БД при чтении деталей задачи")
        return bot.send_message(cid, "❗ Не могу показать задачу.", message_thread_id=tid)

    # ────────── новый вид ──────────
    # одна строка для задачи
    txt = f"*Задача:* {text}\n"           # ← без «\n» после текста
    txt += f"*Поставил:* {author}\n"
    txt += f"*Статус:* {human}"
    if taker:
        txt += f"\n*Принял:* {taker}"
    # ───────────────────────────────

    kb = details_kb(status_key, tid)
    try:
        bot.send_message(cid, txt,
                         parse_mode='Markdown',
                         reply_to_message_id=mid,
                         reply_markup=kb,
                         message_thread_id=tid)
    except ApiTelegramException:
        logger.exception("Ошибка API при выводе деталей")
        bot.reply_to(cb.message, "❗ Не удалось отправить детали.")
    finally:
        bot.answer_callback_query(cb.id)

# ─── «Назад к списку» ──────────────────────────────────────────────────────────

# ——— 2) «Назад к списку» из деталей задачи —————————————————————————————————
@bot.callback_query_handler(lambda cb: cb.data.startswith('back_list|'))
def cb_back_list(cb):
    try:
        # cb.data == "back_list|<status_key>|<thread_id>"
        _, status_key, tid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id)

    human = {'ne':'не выполнено', 'accepted':'принято'}[status_key]

    # Снова достаём список из БД
    try:
        mids = db.get_tasks_by_status(cid, tid, human)
    except DatabaseError:
        logger.exception("DB error in cb_back_list")
        return bot.send_message(cid,
            "❗ Не удалось получить задачи. Повторите позже.",
            message_thread_id=tid)

    if not mids:
        return bot.answer_callback_query(cb.id, text="Нет задач", show_alert=True)

    # И снова передаём chan_id в list_kb
    kb = list_kb(cid, mids, status_key, tid)
    try:
        bot.edit_message_text(f"📋 Задачи «{human}»:",
                              cid, cb.message.message_id,
                              reply_markup=kb)
    except ApiTelegramException:
        logger.exception("API error editing back_list menu")
        bot.send_message(cid,
            "❗ Не удалось обновить список.",
            message_thread_id=tid)
    finally:
        bot.answer_callback_query(cb.id, show_alert=False)

# ——— 3) Кнопка «📨 Прислать все» из меню фильтра —————————————————————
@bot.callback_query_handler(lambda cb: cb.data.startswith('send_all|'))
def cb_send_all(cb):
    try:
        # cb.data == "send_all|<status_key>|<thread_id>"
        _, status_key, tid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id, text="Неверный формат", show_alert=True)

    human = {'ne':'не выполнено', 'accepted':'принято'}[status_key]

    # 1) Получаем список задач
    try:
        mids = db.get_tasks_by_status(cid, tid, human)
    except DatabaseError:
        logger.exception("DB error in cb_send_all")
        return bot.send_message(
            cid,
            "❗ Не удалось загрузить задачи.",
            message_thread_id=tid
        )

    if not mids:
        return bot.answer_callback_query(cb.id, text="Нет задач для отправки", show_alert=False)

    # 2) Рассылаем каждую
    sent = 0
    for mid in mids:
        try:
            author, text, status, taker = db.get_task_by_id(cid, tid, mid)
        except:
            continue

        msg = f"{text}\n\nПоставил: {author}\nСтатус: {status}"
        if taker:
            msg += f"\nПринял: {taker}"

        try:
            bot.send_message(
                cid,
                msg,
                reply_to_message_id=mid,
                parse_mode='Markdown',
                message_thread_id=tid
            )
            sent += 1
        except ApiTelegramException as e:
            # игнорируем отдельные ошибки Markdown/429/etc
            continue

    # 3) Обновляем клавиатуру: убираем «Прислать все», оставляем только список + «К статусам»
    kb = InlineKeyboardMarkup()
    for mid in mids:
        author, text, _, taker = db.get_task_by_id(cid, tid, mid)
        label = text if len(text)<20 else text[:20]+'…'
        cb_data = f"task|{mid}|{status_key}|{tid}"
        kb.add(InlineKeyboardButton(label, callback_data=cb_data))
    kb.add(InlineKeyboardButton("◀ К статусам", callback_data=f"back_status|{tid}"))

    try:
        bot.edit_message_reply_markup(
            chat_id=cid,
            message_id=cb.message.message_id,
            reply_markup=kb
        )
    except ApiTelegramException:
        # если меню удалено или нет прав — молча пропускаем
        pass

    # 4) Тост о результате
    bot.answer_callback_query(cb.id, text=f"Отправлено: {sent} задач", show_alert=False)

# ─── (по аналогии можно добавить send_all callback) ─────────────────────────────

# ─── ЗАПУСК ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling()
