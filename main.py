import time
import telebot
import logging
from sqlite3 import DatabaseError
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import db

TOKEN = '8081090023:AAHizaGHTAshsYhPi7dOePK_slGyPnxQDxU'
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')
db.create_tables()
user_states = {}
logger = logging.getLogger(__name__)

# ——————————————————————————————————————————————————————————————
# Клавиатуры
# ——————————————————————————————————————————————————————————————

def action_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Принято", callback_data="accepted"))
    return kb

def status_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Не выполнено",  callback_data="status_ne"))
    kb.add(InlineKeyboardButton("Принято",        callback_data="status_accepted"))
    return kb

# ——————————————————————————————————————————————————————————————
# Хендлеры команд
# ——————————————————————————————————————————————————————————————

@bot.message_handler(commands=['start'])
def cmd_start(m):
    bot.send_message(
        m.chat.id,
        "Привет! Доступные команды:\n"
        "/newtask — создать задачу\n"
        "/task    — показать все задачи\n"
        "/filter  — отфильтровать задачи",
        message_thread_id=m.message_thread_id 
    )

@bot.message_handler(commands=['newtask'])
def cmd_newtask(m):
    try:
        # Переводим пользователя в состояние «ждём текст задачи»
        user_states[m.from_user.id] = 'await_text'
        bot.send_message(
            m.chat.id,
            "Введите текст задачи:",
            message_thread_id=m.message_thread_id
        )
    except ApiTelegramException as e:
        logger.exception("Telegram API error in cmd_newtask")
        bot.reply_to(m, "Не удалось связаться с Telegram. Попробуйте позже.")
        # Откатим состояние — чтобы пользователь мог на повторный /newtask
        user_states.pop(m.from_user.id, None)


@bot.message_handler(
    func=lambda m: user_states.get(m.from_user.id) == 'await_text',
    content_types=['text']
)
def handle_newtask_text(m):
    cid  = m.chat.id
    tid   = m.message_thread_id
    user = m.from_user
    text = m.text
    author = f"@{user.username}" if user.username \
             else user.first_name or str(user.id)
    
    # Собираем Markdown-текст
    task_md = (
        f"*Задача:*\n"
        f"{text}\n"
        f"*Поставил:* {author}\n"
        f"*Статус:* ❗ Не выполнено"
    )
    
    try:
        # Пытаемся отправить сообщение в Telegram
        msg = bot.send_message(
            cid,
            task_md,
            reply_markup=action_kb(),
            parse_mode='Markdown',
            message_thread_id=tid
        )
    except ApiTelegramException as e:
    # 2) Обрабатываем ошибку API
        try:
            desc = e.result_json.get('description', "")
        except Exception:
            desc = str(e)

        if 'parse entities' in desc.lower() or 'cant parse entities' in desc.lower():
            # Специально реагируем на неверные Markdown-символы
            bot.reply_to(
                m,
                "⚠️ Не удалось отправить задачу из-за недопустимых символов.\n"
                "Уберите или отразите `*`, `_`, `[`, `]`, `(`, `)` и т.п.\n"
                "Например: `привет\\_мир` вместо `привет_мир`."
            )
        else:
            # Любая другая ошибка Telegram API
            logger.exception("Telegram API error sending new task")
            bot.reply_to(m, "Не удалось отправить задачу. Попробуйте позже.")


    else:
        # 3) Если отправка прошла успешно — сохраняем в БД
        try:
            db.add_task(cid, tid, msg.message_id, author, text, 'не выполнено', accepted_by=None)
        except DatabaseError:
            logger.exception("Database error adding new task")
            # Откатываем: удаляем уже отправленное сообщение
            try:
                bot.delete_message(cid, msg.message_id)
            except ApiTelegramException:
                pass
            bot.reply_to(m, "Не удалось сохранить задачу. Попробуйте снова.")
    finally:
        # 4) В любом случае — очищаем состояние пользователя
        user_states.pop(m.from_user.id, None)


@bot.message_handler(commands=['task'])
def cmd_task(m):
    cid  = m.chat.id
    tid = m.message_thread_id
    try:
        mids = db.get_all_tasks(cid, tid)
    except DatabaseError:
        logger.exception("Database error fetching all tasks")
        return bot.reply_to(m, "❗ Не удалось загрузить задачи из базы. Попробуйте позже.")
    
    if not mids:
        return bot.send_message(cid, "📭 Нет задач в этом чате.", message_thread_id=tid)

    error_notified = False

    for mid in mids:
        try:
            author, text, status, accepted_by = db.get_task_by_id(cid, tid, mid)
        except DatabaseError:
            logger.exception(f"DB error fetching task {mid}")
            if not error_notified:
                bot.reply_to(m, "⚠️ Некоторая информация по задачам недоступна.")
                error_notified = True
            continue
        txt = (
            f"*Задача:*\n{text}\n\n"
            f"Поставил: {author}\n"
            f"Статус: {status}"
        )
        if accepted_by:
            txt += f"\nПринял: {accepted_by}"
        
        try:
            bot.send_message(
                cid,
                txt,
                reply_to_message_id=mid,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                message_thread_id=tid
            )
        except ApiTelegramException as e:
            desc = ""
            # Анализируем описание ошибки
            try:
                desc = e.result_json.get('description','').lower()
            except:
                desc = str(e).lower()
            
            if 'parse entities' in desc:
                # Повторяем без Markdown
                bot.send_message(
                    cid,
                    txt,
                    reply_to_message_id=mid,
                    parse_mode=None,
                    disable_web_page_preview=True,
                    message_thread_id=tid
                )
            else:
                logger.exception(f"Tg API error on task {mid}: {desc}")
                if not error_notified:
                    bot.reply_to(m, "❗ Не удалось полностью отобразить все задачи.")
                    error_notified = True
                # и дальше просто продолжаем цикл

    # конец цикла — можно по желанию ещё что-то добавить

@bot.message_handler(commands=['filter'])
def cmd_filter(m):
    tid = m.message_thread_id
    try:
        bot.send_message(
            m.chat.id,
            "Выберите статус:",
            reply_markup=status_kb(),
            message_thread_id=tid 
        )
    except ApiTelegramException as e:
        # Пытаемся получить текст ошибки от Telegram
        try:
            desc = e.result_json.get('description', '').lower()
        except Exception:
            desc = str(e).lower()
        
        # Обрабатываем самые частые случаи:
        if 'bot was blocked by the user' in desc or 'forbidden: user is blocked' in desc:
            bot.reply_to(
                m,
                "❌ Кажется, вы заблокировали бота. Разблокируйте его, чтобы пользоваться командами."
            )
        elif 'bot was kicked' in desc or 'forbidden' in desc:
            bot.reply_to(
                m,
                "❌ У меня нет прав в этом чате. Попросите админа добавить бота и дать ему право писать сообщения."
            )
        elif 'chat not found' in desc:
            bot.reply_to(
                m,
                "❌ Не могу найти этот чат. Возможно, бот был удалён или чат переименован."
            )
        elif 'message_thread_id_invalid' in desc:
            bot.reply_to(
                m,
                "⚠️ Команда /filter работает только в обсуждениях (threads). Перейдите в тему и повторите."
            )
        elif 'bad request: reply markup' in desc:
            bot.reply_to(
                m,
                "⚠️ Не удалось показать кнопки. Попробуйте перезапустить бота или сообщите разработчику."
            )
        else:
            # универсальная «что-то пошло не так»
            bot.reply_to(
                m,
                "❗ Произошла ошибка при отправке меню фильтра. Попробуйте ещё раз через минуту."
            )

# ——————————————————————————————————————————————————————————————
# Обработчики inline-кнопок
# ——————————————————————————————————————————————————————————————

# 1) Нажали «Принято»
@bot.callback_query_handler(func=lambda cb: cb.data == 'accepted')
def handle_accepted(cb):
    tid = cb.message.message_thread_id
    cid = cb.message.chat.id
    mid = cb.message.message_id
    user = cb.from_user

    # Убираем «кружок загрузки» сразу, чтобы не висело
    bot.answer_callback_query(cb.id, show_alert=False)

    # 1) Получаем автора и текст из БД
    try:
        author, text, _, _ = db.get_task_by_id(cid, tid, mid)
    except DatabaseError:
        logger.exception(f"DB error getting task {mid}")
        return bot.send_message(
            cid,
            "❗ Не удалось получить данные задачи. Попробуйте чуть позже."
        )
    

    # 2) Собираем новый текст
    taker = f"@{user.username}" if user.username else user.first_name or str(user.id)
    new_text = (
        f"*Задача:*\n{text}\n"
        f"*Поставил:* {author}\n"
        f"*Принял:* {taker}\n"
        f"*Статус:* ✅ Принято"
    )

    # 3) Пытаемся отредактировать сообщение
    try:
        bot.edit_message_text(
            new_text,
            chat_id=cid,
            message_id=mid,
            parse_mode='Markdown',
            disable_web_page_preview=True,
        )
    except ApiTelegramException as e:
        # разбор описания ошибки
        try:
            desc = e.result_json.get('description', '').lower()
        except Exception:
            desc = str(e).lower()
        
        if 'message is not modified' in desc:
            # пользователь нажал «Принять» повторно
            bot.send_message(
                cid,
                "ℹ️ Эта задача уже была помечена как принятой.",
                message_thread_id=tid
            )
        elif 'chat not found' in desc:
            bot.send_message(
                cid,
                "❌ Не могу найти этот чат. "
                "Возможно, меня удалили или чат переименовали.",
                message_thread_id=tid
            )
        elif 'message to edit not found' in desc:
            bot.send_message(
                cid,
                "⚠️ Исходное сообщение задачи удалено. "
                "Я не могу обновить статус.",
                message_thread_id=tid
            )
        elif 'cant parse entities' in desc or 'parse entities' in desc:
            bot.send_message(
                cid,
                "⚠️ Не удалось применить форматирование Markdown. "
                "Пожалуйста, убедитесь, что в тексте задачи нет необработанных символов "
                "(`*`, `_`, `[`, `]`, `(`, `)`).",
                message_thread_id=tid
            )
        else:
            logger.exception(f"Tg API error editing message {mid}: {desc}")
            bot.send_message(
                cid,
                "❗ Не удалось обновить задачу. Попробуйте через несколько секунд.",
                message_thread_id=tid
            )
        return
    
    # 4) Обновляем статус в базе
    try:
        db.update_task_status(cid, cb.message.message_thread_id, mid, 'принято', accepted_by=taker)
    except DatabaseError:
        logger.exception(f"DB error updating task {mid}")
        return bot.send_message(cid, "❗ Не удалось сохранить статус задачи. Попробуйте позже.", message_thread_id=tid)

    # 5) Вместо второго сообщения в чат — выводим тост в клиенте Telegram
    bot.answer_callback_query(cb.id, text="✅ Задача принята!", show_alert=False)



# 2) Фильтрация по статусу + кнопка «Прислать все»
@bot.callback_query_handler(func=lambda cb: cb.data in ('status_ne','status_accepted'))
def handle_status_filter(cb):
    tid  = cb.message.message_thread_id
    cid  = cb.message.chat.id
    data = cb.data
    st   = {'status_ne':'не выполнено','status_accepted':'принято'}[data]


    try:
        mids = db.get_tasks_by_status(cid, tid, st)
    except DatabaseError:
        logger.exception(f"DB error fetching tasks with status={st} in chat={cid}, thread={tid}")
        # отвечаем кратко — попробуйте позже
        bot.answer_callback_query(cb.id)
        return bot.send_message(
            cid,
            "❗ Не удалось получить задачи из базы. Попробуйте через минуту.",
            message_thread_id=tid
        )
    

    # 2) Формируем клавиатуру и текст
    if not mids:
        text = f"❌ Нет задач со статусом «{st}»."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="back_filter")]])
    else:
        text = f"📋 Задачи со статусом «{st}»:"
        kb = InlineKeyboardMarkup()
        for mid in mids:
            try:
                author, task_text, status, accepted_by = db.get_task_by_id(cid, tid, mid)
            except DatabaseError:
                logger.exception(f"DB error fetching task id={mid}")
                # если одна из задач не читается, пропускаем её
                continue
            label = task_text if len(task_text) < 25 else task_text[:25] + '…'
            kb.add(InlineKeyboardButton(label, callback_data=f"task_{mid}_{data}"))
        kb.add(InlineKeyboardButton("📨 Прислать все", callback_data=f"send_all_{data}"))
        kb.add(InlineKeyboardButton("◀ Назад",         callback_data="back_filter"))
    
    # 3) Пытаемся обновить сообщение с клавиатурой
    try:
        bot.edit_message_text(
            text,
            chat_id=cid,
            message_id=cb.message.message_id,
            reply_markup=kb
        )
    except ApiTelegramException as e:
        # разбор описания ошибки
        try:
            desc = e.result_json.get('description','').lower()
        except Exception:
            desc = str(e).lower()

            # 3.1) Клавиатура сломана (invalid reply_markup)
        if 'reply markup' in desc:
            bot.answer_callback_query(cb.id)
            return bot.send_message(
                cid,
                text,
                message_thread_id=tid
            )
        # 3.2) Чат или тема недоступны
        if 'chat not found' in desc or 'forbidden' in desc:
            bot.answer_callback_query(cb.id)
            return bot.send_message(
                cid,
                "❌ Не могу изменить меню — проверьте, есть ли у бота права в этом чате.",
                message_thread_id=tid
            )
        # 3.3) Сообщение удалено
        if 'message to edit not found' in desc:
            bot.answer_callback_query(cb.id)
            return bot.send_message(
                cid,
                "⚠️ Исходное меню удалено, я не могу его обновить.",
                message_thread_id=tid
            )
        # 3.4) Любая другая ошибка API
        logger.exception(f"Tg API error editing status filter: {desc}")
        bot.answer_callback_query(cb.id)
        return bot.send_message(
            cid,
            "❗ Не удалось показать фильтр. Повторите через несколько секунд.",
            message_thread_id=tid
        )
    # 4) Сообщаем клиенту, что всё OK (всплывашка, не засоряет чат)
    bot.answer_callback_query(cb.id, text="✅ Меню обновлено", show_alert=False)


# 3) Прислать все задачи выбранного статуса
@bot.callback_query_handler(func=lambda cb: cb.data.startswith('send_all_'))
def handle_send_all(cb):
    tid        = cb.message.message_thread_id
    cid        = cb.message.chat.id
    status_cd  = cb.data[len('send_all_'):]
    st         = {'status_ne':'не выполнено','status_accepted':'принято'}[status_cd]

    # 1) Получаем список задач из БД
    try:
        mids       = db.get_tasks_by_status(cid, tid, st)
    except DatabaseError:
        logger.exception(f"DB error fetching tasks with status={st}")
        bot.answer_callback_query(cb.id)
        return bot.send_message(
            cid,
            "❗ Не удалось загрузить задачи из базы. Попробуйте позже.",
            message_thread_id=tid
        )
    # 2) Если нет задач — сразу ответим
    if not mids:
        bot.answer_callback_query(cb.id, text="Нет задач для отправки.")
        return
    
    sent_count = 0

     # 3) Пробуем отправить каждую задачу
    for mid in mids:
        # 3.1) Сначала читаем данные задачи
        try:
            author, text_task, status, accepted_by = db.get_task_by_id(cid, tid, mid)
        except DatabaseError:
            logger.exception(f"DB error fetching task id={mid}")
            # пропускаем эту задачу
            continue
        
        txt = f"{text_task}\n\nПоставил: {author}\nСтатус: {status}"
        if accepted_by:
            txt += f"\nПринял: {accepted_by}"

        # 3.2) Отправляем сообщение
        try:
            bot.send_message(
                cid,
                txt,
                reply_to_message_id=mid,
                parse_mode='Markdown',
                message_thread_id=tid
            )
        except ApiTelegramException as e:
            # разбираем ответ Telegram
            json = getattr(e, 'result_json', {}) or {}
            error_code = json.get('error_code')
            desc = json.get('description', '').lower()

             # 3.2.1) Слишком часто (Flood) — подождать retry_after
            if error_code == 429:
                retry = json.get('parameters', {}).get('retry_after', 'несколько')
                return bot.answer_callback_query(cb.id, text=f"Слишком часто — подождите {retry} сек.")
            
            # 3.2.2) Ошибка Markdown
            if 'parse entities' in desc:
                bot.send_message(
                    cid,
                    txt,
                    reply_to_message_id=mid,
                    parse_mode=None,
                    message_thread_id=tid
                )
                sent_count += 1
                continue

            # 3.2.3) Нет прав или чат недоступен
            if 'forbidden' in desc or 'chat not found' in desc:
                bot.answer_callback_query(cb.id)
                return bot.send_message(
                    cid,
                    "❌ У меня нет прав или чат недоступен. Проверьте настройки бота.",
                    message_thread_id=tid
                )
            
            # 3.2.4) Любая другая ошибка
            logger.exception(f"Tg API error sending task {mid}: {desc}")
            bot.answer_callback_query(cb.id)
            return bot.send_message(
                cid,
                "❗ Не удалось отправить все задачи. Попробуйте позже.",
                message_thread_id=tid
            )
        else:
            sent_count += 1
    # 4) Убираем кнопку «Прислать все» и возвращаем обычные кнопки списка
    kb = InlineKeyboardMarkup()
    for mid in mids:
        try:
            author, text_task, status, accepted_by = db.get_task_by_id(cid, tid, mid)
        except DatabaseError:
            logger.exception(f"DB error fetching task id={mid}")
            continue
        label = text_task if len(text_task) < 25 else text_task[:25] + '…'
        kb.add(InlineKeyboardButton(label, callback_data=f"task_{mid}_{status_cd}"))
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_filter"))

    try:
        bot.edit_message_reply_markup(
            chat_id=cid,
            message_id=cb.message.message_id,
            reply_markup=kb
        )
    except ApiTelegramException as e:
        desc = (getattr(e, 'result_json', {}) or {}).get('description', '').lower()
        # меню удалено
        if 'message to edit not found' in desc:
            return bot.send_message(
                cid,
                "⚠️ Исходное меню удалено – не могу обновить.",
                message_thread_id=tid
            )
        # невалидная клавиатура
        if 'reply markup' in desc:
            return bot.send_message(cid, "⚠️ Не удалось отобразить кнопки.", message_thread_id=tid)
        # нет прав
        if 'forbidden' in desc or 'chat not found' in desc:
            return bot.send_message(
                cid,
                "❌ У меня нет прав в этом чате.",
                message_thread_id=tid
            )
        logger.exception(f"Tg API error editing reply_markup: {desc}")
        return bot.send_message(
            cid,
            "❗ Не удалось обновить меню. Повторите позже.",
            message_thread_id=tid
        )
    # 5) Подтверждаем количество отправленных задач в виде тоста
    bot.answer_callback_query(cb.id, text=f"Отправлено {sent_count} задач.", show_alert=False)


# 4) Выбор конкретной задачи
@bot.callback_query_handler(func=lambda cb: cb.data.startswith('task_'))
def handle_task_select(cb):
    tid = cb.message.message_thread_id
    cid = cb.message.chat.id
    _, mid_s, status_cd = cb.data.split('_', 2)
    mid = int(mid_s)
    human = {'status_ne':'не выполнено','status_accepted':'принято'}[status_cd]

    # 1) Читаем задачу из БД
    try:
        author, text, status, accepted_by = db.get_task_by_id(cid, tid, mid)
    except DatabaseError:
        logger.exception(f"DB error getting task {mid}")
        bot.answer_callback_query(cb.id)
        return bot.send_message(
            cid,
            "❗ Не удалось получить задачу из базы. Попробуйте чуть позже.",
            message_thread_id=tid
        )
    # 2) Формируем текст и клавиатуру «Назад»
    txt = f"{text}\n\nПоставил: {author}\nСтатус: {status}"
    if accepted_by:
        txt += f"\nПринял: {accepted_by}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="back_filter")]])

    # 3) Посылаем сообщение-детали задачи в ту же тему
    try:
        bot.send_message(
            cid,
            f"🔍 Задача:\n\n{txt}",
            reply_to_message_id=mid,
            reply_markup=kb,
            parse_mode='Markdown',
            message_thread_id=tid
        )
    except ApiTelegramException as e:
        # разбор описания ошибки
        try:
            desc = e.result_json.get('description','').lower()
        except Exception:
            desc = str(e).lower()
        
        # 3.1) Ошибка Markdown-разметки
        if 'cant parse entities' in desc or 'parse entities' in desc:
            return bot.send_message(
                cid,
                f"🔍 Задача:\n\n{txt}",
                reply_to_message_id=mid,
                reply_markup=kb,
                parse_mode=None,
                message_thread_id=tid
            )
        # 3.2) Проблема с клавиатурой (хотя кнопка одна, но на всякий)
        if 'reply markup' in desc:
            return bot.send_message(
                cid,
                f"🔍 Задача:\n\n{txt}",
                reply_to_message_id=mid,
                parse_mode='Markdown',
                message_thread_id=tid
            )
        # 3.3) Бот не имеет прав или чат удалён
        if 'forbidden' in desc or 'chat not found' in desc:
            return bot.send_message(
                cid,
                "❌ Не могу отправить детали задачи — у бота нет доступа к чату или чат недоступен.",
                message_thread_id=tid
            )
        # 3.4) Исходное сообщение удалено
        if 'reply message not found' in desc or 'message to edit not found' in desc:
            return bot.send_message(
                cid,
                "⚠️ Исходное сообщение задачи удалено. Я не могу привязать ответ.",
                message_thread_id=tid
            )
        # 3.5) Любая другая ошибка API
        logger.exception(f"Tg API error sending task details {mid}: {desc}")
        return bot.send_message(
            cid,
            "❗ Не удалось показать задачу. Повторите через несколько секунд.",
            message_thread_id=tid
        )
    # 4) Все прошло успешно — показываем тост в клиенте
    bot.answer_callback_query(cb.id, text="✅ Вот ваша задача", show_alert=False)


# 5) «Назад» в меню фильтра
@bot.callback_query_handler(func=lambda cb: cb.data == 'back_filter')
def handle_back_filter(cb):
    tid = cb.message.message_thread_id 
    cid = cb.message.chat.id
    mid = cb.message.message_id
    text = "Выберите статус:"
    kb = status_kb()

    try:
        # 1) Пробуем вернуть меню «Выберите статус:»
        bot.edit_message_text(
            text,
            cid,
            mid,
            reply_markup=kb,
            parse_mode=None
        )
    except ApiTelegramException as e:
        # 2) Разбираем описание ошибки
        if hasattr(e, 'result_json') and e.result_json and 'description' in e.result_json:
            desc = e.result_json['description'].lower()
        else:
            desc = str(e).lower()
        
        # 2.1) Ничего не изменилось — меню уже таким было
        if 'message is not modified' in desc:
            return bot.answer_callback_query(cb.id)
        
        # 2.2) Проблема с клавиатурой — отправляем просто текст
        if 'reply markup' in desc:
            bot.answer_callback_query(cb.id)
            return bot.send_message(
                cid,
                text,
                message_thread_id=tid
            )
        
        # 2.3) Оригинал меню удалён
        if 'message to edit not found' in desc:
            bot.answer_callback_query(cb.id)
            return bot.send_message(
                cid,
                "⚠️ Оригинал меню удалён — не могу его восстановить.",
                message_thread_id=tid
            )
        
        # 2.4) Бот лишён прав или тема/чат недоступны
        if 'chat not found' in desc or 'forbidden' in desc:
            bot.answer_callback_query(cb.id)
            return bot.send_message(
                cid,
                "❌ Нет доступа к теме. Проверьте, что бот добавлен и имеет права.",
                message_thread_id=tid
            )
        
        # 2.5) Любые другие ошибки — логируем и сообщаем общее
        logger.exception(f"Error in back_filter: {desc}")
        bot.answer_callback_query(cb.id)
        return bot.send_message(
            cid,
            "❗ Не удалось вернуться назад. Повторите попытку через минуту.",
            message_thread_id=tid
        )
    # 3) Успешно вернули меню — небольшой тост в клиенте
    bot.answer_callback_query(cb.id, text="✅ Возврат выполнен", show_alert=False)

# ——————————————————————————————————————————————————————————————
# Запуск polling
# ——————————————————————————————————————————————————————————————

def run_bot():
    while True:
        try:
            bot.infinity_polling()
        except ApiTelegramException:
            logger.exception("Telegram API error, restarting bot in 4 seconds")
            time.sleep(4)
        except Exception:
            logger.exception("Unexpected error, restarting bot in 4 seconds")
            time.sleep(4)

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    run_bot()