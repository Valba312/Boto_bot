import time
import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import db

TOKEN = '8081090023:AAHizaGHTAshsYhPi7dOePK_slGyPnxQDxU'
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')
db.create_tables()
user_states = {}

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
        "/filter  — отфильтровать задачи"
    )

@bot.message_handler(commands=['newtask'])
def cmd_newtask(m):
    user_states[m.from_user.id] = 'await_text'
    bot.send_message(m.chat.id, "Введите текст задачи:")

@bot.message_handler(
    func=lambda m: user_states.get(m.from_user.id) == 'await_text',
    content_types=['text']
)
def handle_newtask_text(m):
    cid  = m.chat.id
    user = m.from_user
    text = m.text

    # Собираем упоминание автора задачи
    if user.username:
        author = f"@{user.username}"
    else:
        author = user.first_name or str(user.id)

    # Сохраняем задачу
    msg = bot.send_message(
        cid,
        f"*Задача:*\n{text}\n*Поставил:* {author}\n*Статус:* ❗ Не выполнено",
        reply_markup=action_kb()
    )
    db.add_task(cid, msg.message_id, author, text, 'не выполнено', accepted_by=None)
    user_states.pop(m.from_user.id, None)

@bot.message_handler(commands=['task'])
def cmd_task(m):
    cid  = m.chat.id
    mids = db.get_all_tasks(cid)
    if not mids:
        bot.send_message(cid, "Нет задач в этом чате.")
        return

    for mid in mids:
        author, text, status, accepted_by = db.get_task_by_id(cid, mid)
        txt = f"{text}\n\nПоставил: {author}\nСтатус: {status}"
        if accepted_by:
            txt += f"\nПринял: {accepted_by}"
        bot.send_message(
            cid,
            txt,
            reply_to_message_id=mid,
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['filter'])
def cmd_filter(m):
    bot.send_message(
        m.chat.id,
        "Выберите статус:",
        reply_markup=status_kb()
    )

# ——————————————————————————————————————————————————————————————
# Обработчики inline-кнопок
# ——————————————————————————————————————————————————————————————

# 1) Нажали «Принято»
@bot.callback_query_handler(func=lambda cb: cb.data == 'accepted')
def handle_accepted(cb):
    cid = cb.message.chat.id
    mid = cb.message.message_id
    user = cb.from_user

    # Собираем упоминание того, кто принял
    if user.username:
        taker = f"@{user.username}"
    else:
        taker = user.first_name or str(user.id)

    # Берём из БД текст и автора
    author, text, _, _ = db.get_task_by_id(cid, mid)

    new = (
        f"*Задача:*\n{text}\n"
        f"*Поставил:* {author}\n"
        f"*Принял:* {taker}\n"
        f"*Статус:* ✅ Принято"
    )
    bot.edit_message_text(new, cid, mid, parse_mode='Markdown')
    db.update_task_status(cid, mid, 'принято', accepted_by=taker)
    bot.answer_callback_query(cb.id)

# 2) Фильтрация по статусу + кнопка «Прислать все»
@bot.callback_query_handler(func=lambda cb: cb.data in ('status_ne','status_accepted'))
def handle_status_filter(cb):
    cid  = cb.message.chat.id
    data = cb.data
    st   = {'status_ne':'не выполнено','status_accepted':'принято'}[data]

    mids = db.get_tasks_by_status(cid, st)
    if not mids:
        bot.edit_message_text(
            f"❌ Нет задач со статусом «{st}».",
            cid,
            cb.message.message_id,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="back_filter")]])
        )
    else:
        kb = InlineKeyboardMarkup()
        for mid in mids:
            author, text, status, accepted_by = db.get_task_by_id(cid, mid)
            label = text if len(text) < 25 else text[:25] + '…'
            kb.add(InlineKeyboardButton(label, callback_data=f"task_{mid}_{data}"))
        kb.add(InlineKeyboardButton("📨 Прислать все", callback_data=f"send_all_{data}"))
        kb.add(InlineKeyboardButton("◀ Назад",         callback_data="back_filter"))

        bot.edit_message_text(
            f"📋 Задачи со статусом «{st}»:",
            cid,
            cb.message.message_id,
            reply_markup=kb
        )
    bot.answer_callback_query(cb.id)

# 3) Прислать все задачи выбранного статуса
@bot.callback_query_handler(func=lambda cb: cb.data.startswith('send_all_'))
def handle_send_all(cb):
    cid        = cb.message.chat.id
    status_cd  = cb.data[len('send_all_'):]
    st         = {'status_ne':'не выполнено','status_accepted':'принято'}[status_cd]
    mids       = db.get_tasks_by_status(cid, st)

    if not mids:
        bot.answer_callback_query(cb.id, text="Нет задач для отправки.")
        return

    try:
        for mid in mids:
            author, text, status, accepted_by = db.get_task_by_id(cid, mid)
            txt = f"{text}\n\nПоставил: {author}\nСтатус: {status}"
            if accepted_by:
                txt += f"\nПринял: {accepted_by}"
            bot.send_message(
                cid,
                txt,
                reply_to_message_id=mid,
                parse_mode='Markdown'
            )
    except ApiTelegramException as e:
        if getattr(e, 'result_json', {}).get('error_code') == 429:
            retry = e.result_json.get('parameters', {}).get('retry_after', 'несколько')
            bot.answer_callback_query(cb.id, text=f"Слишком часто — подожди {retry} сек.")
            return
        else:
            raise

    # Убираем кнопку «Прислать все»
    kb = InlineKeyboardMarkup()
    for mid in mids:
        author, text, status, accepted_by = db.get_task_by_id(cid, mid)
        label = text if len(text) < 25 else text[:25] + '…'
        kb.add(InlineKeyboardButton(label, callback_data=f"task_{mid}_{status_cd}"))
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_filter"))

    bot.edit_message_reply_markup(
        chat_id=cid,
        message_id=cb.message.message_id,
        reply_markup=kb
    )
    bot.answer_callback_query(cb.id, text=f"Отправлено {len(mids)} задач.")

# 4) Выбор конкретной задачи
@bot.callback_query_handler(func=lambda cb: cb.data.startswith('task_'))
def handle_task_select(cb):
    cid = cb.message.chat.id
    _, mid_s, status_cd = cb.data.split('_', 2)
    mid = int(mid_s)
    human = {'status_ne':'не выполнено','status_accepted':'принято'}[status_cd]

    author, text, status, accepted_by = db.get_task_by_id(cid, mid)
    txt = f"{text}\n\nПоставил: {author}\nСтатус: {status}"
    if accepted_by:
        txt += f"\nПринял: {accepted_by}"

    bot.send_message(
        cid,
        f"🔍 Задача:\n\n{txt}",
        reply_to_message_id=mid,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="back_filter")]]),
        parse_mode='Markdown'
    )
    bot.answer_callback_query(cb.id)

# 5) «Назад» в меню фильтра
@bot.callback_query_handler(func=lambda cb: cb.data == 'back_filter')
def handle_back_filter(cb):
    bot.edit_message_text(
        "Выберите статус:",
        cb.message.chat.id,
        cb.message.message_id,
        reply_markup=status_kb()
    )
    bot.answer_callback_query(cb.id)

# ——————————————————————————————————————————————————————————————
# Запуск polling
# ——————————————————————————————————————————————————————————————

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True, skip_pending=False)
