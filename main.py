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
    # 1) Парсинг callback_data
    try:
        _, tid_s, mid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        mid = int(mid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id,
                                        "❗ Неверные данные кнопки. Попробуйте ещё раз.",
                                        show_alert=True)
    # 2) Формирование имени того, кто принял
    try:
        user = cb.from_user
        taker = f"@{user.username}" if user.username else user.first_name or str(user.id)
    except Exception:
        logger.exception("Ошибка при чтении данных пользователя")
        taker = "<unknown>"

    # 3) Чтение задачи из БД
    try:
        row = db.get_task_by_id(cid, tid, mid)
        if not row:
            raise LookupError("Задача не найдена")
        author, text, _, _ = row
    except LookupError:
        logger.warning("Попытка принять несуществующую задачу")
        return bot.answer_callback_query(cb.id,
                                        "❗ Задача не найдена.",
                                        show_alert=True)
    except Exception:
        logger.exception("Ошибка БД при чтении задачи для принятия")
        return bot.answer_callback_query(cb.id,
                                        "❗ Не удалось прочесть задачу.",
                                        show_alert=True)

    # 4) Обновление статуса в БД
    try:
        db.update_task_status(cid, tid, mid, 'принято', taker)
    except Exception:
        logger.exception("Ошибка БД при обновлении статуса")
        # уведомляем пользователя, но не выходим — можно попытаться обновить UI
        bot.answer_callback_query(cb.id,
                                  "❗ Статус не сохранён. Попробуйте позже.",
                                  show_alert=True)

    # 5) Экранирование для HTML
    try:
        text_esc   = html.escape(text)
        author_esc = html.escape(author)
        taker_esc  = html.escape(taker)
    except Exception:
        logger.exception("Ошибка html.escape")
        text_esc, author_esc, taker_esc = text, author, taker

    # 6) Формирование нового текста
    new_html = (
        f"<s><b>Задача:</b> {text_esc}</s>\n\n"
        f"<b>Принял:</b> {taker_esc}\n"
        f"<b>Статус:</b> ✅ Принято"
    )

    # 7) Редактирование сообщения в чате
    try:
        bot.edit_message_text(
            new_html,
            chat_id=cid,
            message_id=mid,
            parse_mode='HTML',
            reply_markup=None
        )
    except ApiTelegramException as e:
        # Игнорируем «message is not modified», логируем все прочие ошибки
        err_desc = getattr(e, 'result_json', {}).get('description', '')
        if not (e.error_code == 400 and 'message is not modified' in err_desc):
            logger.exception("Не удалось обновить сообщение после принятия")
    except Exception:
        logger.exception("Непредвиденная ошибка при edit_message_text")


    # 8) Финальное уведомление о клике
    try:
        bot.answer_callback_query(cb.id,
                                  "✅ Задача помечена как принята")
    except ApiTelegramException:
        logger.exception("Ошибка при answer_callback_query в конце")

# ─── /filter ───────────────────────────────────────────────────────────────────
@bot.message_handler(commands=['filter'])
def cmd_filter(m):
    # 1) Определяем chat_id
    try:
        cid = m.chat.id
    except AttributeError:
        logger.exception("m.chat.id отсутствует")
        return bot.reply_to(
            m,
            "❗ Не удалось определить чат.",
            message_thread_id=getattr(m, 'message_thread_id', None)
        )

    # 2) Определяем thread_id (если есть)
    tid = getattr(m, 'message_thread_id', None)

    # 3) Формируем клавиатуру статусов
    try:
        kb = status_kb(tid)
    except Exception:
        logger.exception("Ошибка при формировании клавиатуры статусов")
        return bot.reply_to(
            m,
            "❗ Не удалось сформировать меню статусов.",
            message_thread_id=tid
        )

    # 4) Отправляем сообщение с клавиатурой
    try:
        bot.send_message(
            cid,
            "Выберите статус:",
            reply_markup=kb,
            message_thread_id=tid
        )
    except ValueError:
        logger.exception("Неправильные параметры для send_message")
        return bot.reply_to(
            m,
            "❗ Внутренняя ошибка форматирования меню.",
            message_thread_id=tid
        )
    except ApiTelegramException:
        logger.exception("ApiTelegramException при send_message в /filter")
        return bot.reply_to(
            m,
            "❗ Не удалось показать меню фильтра. Проверьте права бота.",
            message_thread_id=tid
        )
    except Exception:
        logger.exception("Неожиданная ошибка при отправке меню фильтра")
        return bot.reply_to(
            m,
            "❗ Произошла непредвиденная ошибка. Попробуйте позже.",
            message_thread_id=tid
        )

# ─── «Статус → список» ─────────────────────────────────────────────────────────

# ——— 1) Статус → список задач ————————————————————————————————————————————
@bot.callback_query_handler(lambda cb: cb.data.startswith('status|'))
def cb_status(cb):
    # 1) Парсинг callback_data
    try:
        _, status_key, tid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id,
                                         "❗ Ошибка формата данных.",
                                         show_alert=True)
    except Exception:
        logger.exception("Непредвиденная ошибка при разборе callback_data")
        return bot.answer_callback_query(cb.id,
                                         "❗ Внутренняя ошибка.",
                                         show_alert=True)

    # 2) Преобразование ключа статуса
    try:
        human = {'ne': 'не выполнено', 'accepted': 'принято'}[status_key]
    except KeyError:
        logger.warning(f"Неизвестный статус: {status_key}")
        return bot.answer_callback_query(cb.id,
                                         "❗ Неверный статус.",
                                         show_alert=True)

    # 3) Получение списка задач из БД
    try:
        mids = db.get_tasks_by_status(cid, tid, human)
    except DatabaseError:
        logger.exception("DB error in cb_status")
        return bot.send_message(cid,
                                "❗ Не удалось получить список задач. Повторите позже.",
                                message_thread_id=tid)
    except Exception:
        logger.exception("Неожиданная ошибка при запросе задач")
        return bot.send_message(cid,
                                "❗ Внутренняя ошибка при получении задач.",
                                message_thread_id=tid)

    # 4) Формирование и отправка меню
    if not mids:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("◀ К статусам", callback_data=f"back_status|{tid}")
        )
        try:
            bot.edit_message_text(
                f"❌ Нет задач «{human}».",
                chat_id=cid,
                message_id=cb.message.message_id,
                reply_markup=kb
            )
        except ApiTelegramException as e:
            desc = e.result_json.get('description', '')
            # Обработка rate limit 429
            if e.error_code == 429 and 'retry after' in desc:
                tag = 'retry after '
                idx = desc.find(tag)
                retry = None
                if idx != -1:
                    after = desc[idx + len(tag):].strip()
                    num = after.split()[0] if after.split() else ''
                    try:
                        retry = int(num)
                    except ValueError:
                        retry = None
                if retry is not None:
                    bot.answer_callback_query(
                        cb.id,
                        f"❗ Слишком много запросов. Повторите через {retry} сек.",
                        show_alert=True
                    )
                    return
            # Игнорируем «message is not modified»
            if not (e.error_code == 400 and 'message is not modified' in desc):
                logger.exception("Не удалось обновить сообщение при отсутствии задач")
        except Exception:
            logger.exception("Неожиданная ошибка при edit_message_text (нет задач)")
    else:
        kb = list_kb(cid, mids, status_key, tid)
        try:
            bot.edit_message_text(
                f"📋 Задачи «{human}»:",
                chat_id=cid,
                message_id=cb.message.message_id,
                reply_markup=kb
            )
        except ApiTelegramException as e:
            desc = e.result_json.get('description', '')
            # Обработка rate limit 429
            if e.error_code == 429 and 'retry after' in desc:
                tag = 'retry after '
                idx = desc.find(tag)
                retry = None
                if idx != -1:
                    after = desc[idx + len(tag):].strip()
                    num = after.split()[0] if after.split() else ''
                    try:
                        retry = int(num)
                    except ValueError:
                        retry = None
                if retry is not None:
                    bot.answer_callback_query(
                        cb.id,
                        f"❗ Слишком много запросов. Повторите через {retry} сек.",
                        show_alert=True
                    )
                    return
            # Игнорируем «message is not modified»
            if not (e.error_code == 400 and 'message is not modified' in desc):
                logger.exception("Не удалось обновить список задач")
        except Exception:
            logger.exception("Неожиданная ошибка при edit_message_text (список задач)")

    # 5) Закрываем callback_query
    try:
        bot.answer_callback_query(cb.id, show_alert=False)
    except ApiTelegramException:
        logger.warning("ApiTelegramException при answer_callback_query в cb_status", exc_info=True)
    except Exception:
        logger.exception("Непредвиденная ошибка при ответе callback_query в cb_status")

# ─── «Назад к статусам» ────────────────────────────────────────────────────────

@bot.callback_query_handler(lambda cb: cb.data.startswith('back_status|'))
def cb_back_status(cb):
    # 1) Парсинг callback_data
    try:
        _, tid_s = cb.data.split('|', 1)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(
            cb.id,
            "❗ Неверный формат данных.",
            show_alert=True
        )
    except Exception:
        logger.exception("Ошибка разбора данных callback back_status")
        return bot.answer_callback_query(
            cb.id,
            "❗ Внутренняя ошибка.",
            show_alert=True
        )

    # 2) Формирование клавиатуры статусов
    try:
        kb = status_kb(tid)
    except Exception:
        logger.exception("Ошибка при формировании клавиатуры статусов")
        return bot.answer_callback_query(
            cb.id,
            "❗ Не удалось сформировать меню статусов.",
            show_alert=True
        )

    # 3) Редактирование сообщения
    try:
        bot.edit_message_text(
            "Выберите статус:",
            chat_id=cid,
            message_id=cb.message.message_id,
            reply_markup=kb
        )
    except ApiTelegramException as e:
        desc = e.result_json.get('description', '')
        # 3a) Rate limit 429
        if e.error_code == 429 and 'retry after' in desc:
            tag = 'retry after '
            idx = desc.find(tag)
            retry = None
            if idx != -1:
                after = desc[idx + len(tag):].split()[0]
                try:
                    retry = int(after)
                except ValueError:
                    retry = None
            msg = (f"❗ Слишком много запросов. Повторите через {retry} сек."
                   if retry else "❗ Слишком много запросов. Повторите позже.")
            return bot.answer_callback_query(cb.id, msg, show_alert=True)
        # 3b) Игнорировать «message is not modified»
        if e.error_code == 400 and 'message is not modified' in desc:
            pass
        else:
            logger.exception("Ошибка API при редактировании сообщения back_status")
    except Exception:
        logger.exception("Неожиданная ошибка при edit_message_text back_status")
    finally:
        # 4) Закрываем callback_query
        try:
            bot.answer_callback_query(cb.id)
        except Exception:
            logger.exception("Ошибка при ответе callback_query back_status")

# ─── «Выбор задачи → детали» ───────────────────────────────────────────────────

@bot.callback_query_handler(lambda cb: cb.data.startswith('task|'))
def cb_task(cb):
    # 1) Парсинг callback_data
    try:
        _, mid_s, status_key, tid_s = cb.data.split('|', 3)
        mid = int(mid_s)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id,
                                         "❗ Некорректные данные кнопки.",
                                         show_alert=True)
    except Exception:
        logger.exception("Ошибка при разборе данных callback в cb_task")
        return bot.answer_callback_query(cb.id,
                                         "❗ Внутренняя ошибка.",
                                         show_alert=True)

    # 2) Проверка статуса
    try:
        human = {'ne': 'не выполнено', 'accepted': 'принято'}[status_key]
    except KeyError:
        logger.warning(f"Неизвестный статус: {status_key}")
        return bot.answer_callback_query(cb.id,
                                         "❗ Неверный статус задачи.",
                                         show_alert=True)

    # 3) Чтение из БД
    try:
        result = db.get_task_by_id(cid, tid, mid)
        if not result:
            raise LookupError(f"Задача {mid} не найдена")
        author, text, _, taker = result
    except LookupError:
        logger.warning(f"Задача {mid} не найдена в БД")
        return bot.answer_callback_query(cb.id,
                                         "❗ Задача не найдена.",
                                         show_alert=True)
    except DatabaseError:
        logger.exception("Ошибка БД при чтении деталей задачи")
        return bot.send_message(cid,
                                "❗ Не удалось загрузить детали задачи. Повторите позже.",
                                message_thread_id=tid)
    except Exception:
        logger.exception("Непредвиденная ошибка при чтении задачи")
        return bot.send_message(cid,
                                "❗ Внутренняя ошибка при получении задачи.",
                                message_thread_id=tid)

    # 4) Формируем текст и клавиатуру
    txt = f"*Задача:* {text}\n" \
          f"*Поставил:* {author}\n" \
          f"*Статус:* {human}"
    if taker:
        txt += f"\n*Принял:* {taker}"
    kb = details_kb(status_key, tid)

    # 5) Отправка сообщения с деталями
    try:
        bot.send_message(
            cid,
            txt,
            parse_mode='Markdown',
            reply_to_message_id=mid,
            reply_markup=kb,
            message_thread_id=tid
        )
    except ApiTelegramException as e:
        desc = getattr(e, 'result_json', {}).get('description', '')
        # a) Если оригинал удалён
        if e.error_code == 400 and 'message to be replied not found' in desc:
            logger.warning(f"Сообщение {mid} не найдено, отправляем без reply_to")
            bot.send_message(cid, txt,
                             parse_mode='Markdown',
                             reply_markup=kb,
                             message_thread_id=tid)
        # b) Ошибка парсинга Markdown
        elif e.error_code == 400 and "can't parse entities" in desc:
            logger.exception("Ошибка Markdown-разметки в cb_task")
            bot.send_message(cid, txt,
                             parse_mode=None,
                             reply_markup=kb,
                             message_thread_id=tid)
        # c) Rate limit
        elif e.error_code == 429 and 'retry after' in desc:
            # вытаскиваем цифры после 'retry after '
            part = desc.partition('retry after ')[2].split()[0]
            wait = part if part.isdigit() else None
            msg = (f"❗ Слишком много запросов. Повторите через {wait} сек."
                   if wait else "❗ Слишком много запросов. Попробуйте позже.")
            return bot.answer_callback_query(cb.id, msg, show_alert=True)
        else:
            logger.exception("Ошибка API при отправке деталей задачи")
            bot.reply_to(cb.message, "❗ Не удалось показать детали задачи.")
    except Exception:
        logger.exception("Непредвиденная ошибка при send_message в cb_task")
        bot.reply_to(cb.message, "❗ Ошибка при выводе деталей.")
    finally:
        # 6) Закрываем callback
        try:
            bot.answer_callback_query(cb.id)
        except Exception:
            logger.exception("Ошибка при answer_callback_query в cb_task")

# ─── «Назад к списку» ──────────────────────────────────────────────────────────

# ——— 2) «Назад к списку» из деталей задачи —————————————————————————————————
@bot.callback_query_handler(lambda cb: cb.data.startswith('back_list|'))
def cb_back_list(cb):
    # 1) Разбор callback_data
    try:
        _, status_key, tid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id)
    except Exception:
        logger.exception("Ошибка разбора данных в cb_back_list")
        return bot.answer_callback_query(cb.id, "❗ Внутренняя ошибка.", show_alert=True)

    # 2) Проверка статуса
    try:
        human = {'ne':'не выполнено', 'accepted':'принято'}[status_key]
    except KeyError:
        logger.warning(f"Неизвестный статус в cb_back_list: {status_key}")
        return bot.answer_callback_query(cb.id, "❗ Неверный статус.", show_alert=True)

    # 3) Получение списка задач из БД
    try:
        mids = db.get_tasks_by_status(cid, tid, human)
    except DatabaseError:
        logger.exception("DB error in cb_back_list")
        return bot.send_message(cid,
                                "❗ Не удалось получить задачи. Повторите позже.",
                                message_thread_id=tid)
    except Exception:
        logger.exception("Неожиданная ошибка при запросе задач в cb_back_list")
        return bot.send_message(cid,
                                "❗ Внутренняя ошибка при получении задач.",
                                message_thread_id=tid)

    # 4) Если задач нет
    if not mids:
        return bot.answer_callback_query(cb.id, "❗ Нет задач", show_alert=True)

    # 5) Формирование клавиатуры
    try:
        kb = list_kb(cid, mids, status_key, tid)
    except Exception:
        logger.exception("Ошибка при формировании списка задач в cb_back_list")
        return bot.answer_callback_query(cb.id, "❗ Не удалось сформировать меню.", show_alert=True)

    # 6) Обновление текста меню
    try:
        bot.edit_message_text(
            f"📋 Задачи «{human}»:",
            chat_id=cid,
            message_id=cb.message.message_id,
            reply_markup=kb
        )
    except ApiTelegramException as e:
        desc = e.result_json.get('description', '')
        # 6a) Обработка rate limit
        if e.error_code == 429 and 'retry after' in desc:
            tag = 'retry after '
            idx = desc.find(tag)
            retry = None
            if idx != -1:
                part = desc[idx + len(tag):].split()[0]
                retry = int(part) if part.isdigit() else None
            msg = (f"❗ Слишком много запросов. Повторите через {retry} сек."
                   if retry else "❗ Слишком много запросов. Попробуйте позже.")
            return bot.answer_callback_query(cb.id, msg, show_alert=True)
        # 6b) Игнорируем «message is not modified»
        if not (e.error_code == 400 and 'message is not modified' in desc):
            logger.exception("Ошибка API при обновлении меню cb_back_list")
            bot.send_message(cid,
                             "❗ Не удалось обновить список.",
                             message_thread_id=tid)
    except Exception:
        logger.exception("Неожиданная ошибка при edit_message_text в cb_back_list")
        bot.send_message(cid,
                         "❗ Не удалось обновить список.",
                         message_thread_id=tid)
    finally:
        # 7) Закрываем callback_query
        try:
            bot.answer_callback_query(cb.id, show_alert=False)
        except Exception:
            logger.exception("Ошибка при answer_callback_query в cb_back_list")

# ——— 3) Кнопка «📨 Прислать все» из меню фильтра —————————————————————
@bot.callback_query_handler(lambda cb: cb.data.startswith('send_all|'))
def cb_send_all(cb):
    # 1) Разбор callback_data
    try:
        _, status_key, tid_s = cb.data.split('|', 2)
        tid = None if tid_s == 'None' else int(tid_s)
        cid = cb.message.chat.id
    except ValueError:
        return bot.answer_callback_query(cb.id, text="❗ Неверный формат.", show_alert=True)
    except Exception:
        logger.exception("Ошибка разбора данных cb_send_all")
        return bot.answer_callback_query(cb.id, text="❗ Внутренняя ошибка.", show_alert=True)

    # 2) Переводим ключ в текст
    human = {'ne':'не выполнено','accepted':'принято'}.get(status_key)
    if not human:
        return bot.answer_callback_query(cb.id, text="❗ Неверный статус.", show_alert=True)

    # 3) Получаем список задач
    try:
        mids = db.get_tasks_by_status(cid, tid, human)
    except DatabaseError:
        logger.exception("DB error in cb_send_all")
        return bot.send_message(cid, "❗ Не удалось загрузить задачи.", message_thread_id=tid)
    except Exception:
        logger.exception("Неожиданная ошибка при загрузке задач")
        return bot.send_message(cid, "❗ Внутренняя ошибка при загрузке задач.", message_thread_id=tid)

    if not mids:
        return bot.answer_callback_query(cb.id, text="Нет задач для отправки", show_alert=False)

    # 4) Рассылаем каждую
    sent = 0
    for mid in mids:
        try:
            author, text, status, taker = db.get_task_by_id(cid, tid, mid)
        except Exception:
            logger.exception(f"Ошибка чтения задачи {mid}")
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
            desc = e.result_json.get('description', '').lower()

            # 1) «reply_to not found» — просто пропускаем
            if 'message to be replied not found' in desc:
               continue

         # 2) «can't parse entities» — шлём без Markdown
            if "can't parse entities" in desc:
                try:
                    bot.send_message(
                        cid,
                        msg,
                        reply_to_message_id=mid,
                        parse_mode=None,
                        message_thread_id=tid
                    )
                    sent += 1
                except Exception:
                    logger.exception(f"Не удалось отправить задачу {mid} без Markdown")
                continue
            logger.exception(f"ApiTelegramException при отправке задачи {mid}", exc_info=True)
            continue
        except Exception:
            logger.exception(f"Непредвиденная ошибка при отправке задачи {mid}")
            continue

    # 5) Обновляем клавиатуру: убираем «Прислать все»
    try:
        kb = InlineKeyboardMarkup()
        for mid in mids:
            try:
                author, text, _, taker = db.get_task_by_id(cid, tid, mid)
            except Exception:
                logger.exception(f"Ошибка чтения задачи {mid} при обновлении клавиатуры")
                continue
            label = text if len(text) < 20 else text[:20] + '…'
            cb_data = f"task|{mid}|{status_key}|{tid}"
            kb.add(InlineKeyboardButton(label, callback_data=cb_data))
        kb.add(InlineKeyboardButton("◀ К статусам", callback_data=f"back_status|{tid}"))

        bot.edit_message_reply_markup(
            chat_id=cid,
            message_id=cb.message.message_id,
            reply_markup=kb
        )
    except ApiTelegramException:
        # если меню удалено или нет прав — молча пропускаем
        logger.warning("ApiTelegramException при обновлении клавиатуры send_all", exc_info=True)
    except Exception:
        logger.exception("Неожиданная ошибка при обновлении клавиатуры send_all")

    # 6) Финальное уведомление
    try:
        bot.answer_callback_query(cb.id, text=f"Отправлено: {sent} задач", show_alert=False)
    except Exception:
        logger.exception("Ошибка при answer_callback_query в cb_send_all")

# ─── ЗАПУСК ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling()
