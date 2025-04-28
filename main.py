import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import db

TOKEN = '8081090023:AAHizaGHTAshsYhPi7dOePK_slGyPnxQDxU'
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# FSM-словарь
user_states = {}
# create DB
db.create_tables()

# клавиатуры
def status_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Не выполнено", callback_data="status_ne"))
    kb.add(InlineKeyboardButton("Взято в работу", callback_data="status_in"))
    kb.add(InlineKeyboardButton("Выполнено", callback_data="status_done"))
    return kb

def action_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Взять в работу", callback_data="in_progress"))
    kb.add(InlineKeyboardButton("Выполнено", callback_data="completed"))
    return kb

def back_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_status"))
    return kb

# /start
@bot.message_handler(commands=['start'])
def cmd_start(m):
    bot.send_message(m.chat.id, "Привет! /newtask /task /filter")

# /newtask
@bot.message_handler(commands=['newtask'])
def cmd_newtask(m):
    user_states[m.from_user.id] = 'await_text'
    bot.send_message(m.chat.id, "Введите текст задачи:", message_thread_id=m.message_thread_id)

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id)=='await_text', content_types=['text'])
def handle_newtask_text(m):
    text   = m.text
    author = m.from_user.first_name or 'Пользователь'
    cid    = m.chat.id
    tid    = m.message_thread_id

    msg = bot.send_message(
        cid,
        f"*Задача:*\n{text}\n*Поставил:* {author}\n*Статус:* ❗ Не выполнено",
        reply_markup=action_kb(),
        message_thread_id=tid
    )
    db.add_task(cid, tid, msg.message_id, author, text, 'не выполнено')
    user_states.pop(m.from_user.id, None)

# /task
@bot.message_handler(commands=['task'])
def cmd_task(m):
    cid = m.chat.id
    tid = m.message_thread_id
    mids = db.get_all_tasks(cid, tid)
    if not mids:
        bot.send_message(cid, "Нет задач в этой теме.", message_thread_id=tid)
        return
    for mid in mids:
        # Получаем текст и статус из БД
        txt, status = db.get_task_by_id(cid, mid)
        bot.send_message(
            cid,
            f"{txt}\n\nСтатус: {status}",
            reply_to_message_id=mid,
            message_thread_id=tid,
            parse_mode='Markdown'
        )

# /filter
@bot.message_handler(commands=['filter'])
def cmd_filter(m):
    bot.send_message(m.chat.id, "Выберите статус:", reply_markup=status_kb(), message_thread_id=m.message_thread_id)

@bot.callback_query_handler(func=lambda cb: True)
def cb_handler(cb):
    cid = cb.message.chat.id
    tid = cb.message.message_thread_id
    data = cb.data

    # смена статуса кнопками задачи
    if data == 'in_progress':
        new = cb.message.text.replace('Не выполнено', 'Взято в работу ✅')
        bot.edit_message_text(
            new,
            cid,
            cb.message.message_id,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Выполнено", callback_data="completed")
            ]])
        )
        db.update_task_status(cid, cb.message.message_id, 'взято в работу')
        bot.answer_callback_query(cb.id)
        return

    if data == 'completed':
        new = (cb.message.text
                 .replace('Не выполнено', 'Выполнено ✅')
                 .replace('Взято в работу ✅', 'Выполнено ✅'))
        bot.edit_message_text(
            new,
            cid,
            cb.message.message_id,
            parse_mode='Markdown'
        )
        db.update_task_status(cid, cb.message.message_id, 'выполнено')
        bot.answer_callback_query(cb.id)
        return

    # фильтр по статусу
    if data.startswith('status_'):
        status_map = {
            'status_ne':   'не выполнено',
            'status_in':   'взято в работу',
            'status_done': 'выполнено',
        }
        st = status_map[data]
        mids = db.get_tasks_by_status(cid, tid, st)

        if not mids:
            bot.edit_message_text(
                f"Нет задач «{st}».",
                cid,
                cb.message.message_id,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀ Назад", callback_data="back_status")
                ]])
            )
        else:
            kb = InlineKeyboardMarkup()
            for mid in mids:
                txt, _ = db.get_task_by_id(cid, mid)
                label = txt[:25] + '…' if len(txt) > 25 else txt
                kb.add(InlineKeyboardButton(label, callback_data=f"task_{mid}_{data}"))
            kb.add(InlineKeyboardButton("◀ Назад", callback_data="back_status"))

            bot.edit_message_text(
                f"Задачи «{st}»:",
                cid,
                cb.message.message_id,
                reply_markup=kb
            )
        bot.answer_callback_query(cb.id)
        return

    # назад к статусам
    if data == 'back_status':
        bot.edit_message_text(
            "Выберите статус:",
            cid,
            cb.message.message_id,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Не выполнено", callback_data="status_ne")],
                [InlineKeyboardButton("Взято в работу", callback_data="status_in")],
                [InlineKeyboardButton("Выполнено", callback_data="status_done")],
            ])
        )
        bot.answer_callback_query(cb.id)
        return

    # выбор конкретной задачи
    if data.startswith('task_'):
        _, mid_s, data_st = data.split('_', 2)
        mid = int(mid_s)
        st_map = {
            'status_ne':   'не выполнено',
            'status_in':   'взято в работу',
            'status_done': 'выполнено',
        }
        st = st_map[data_st]
        rec = db.get_task_by_id(cid, mid)
        if rec:
            txt, _ = rec
            bot.send_message(
                cid,
                f"Задача:\n\n{txt}\n\nСтатус: {st}",
                reply_to_message_id=mid,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀ Назад", callback_data=data_st)
                ]]),
                message_thread_id=tid,
                parse_mode='Markdown'
            )
        else:
            bot.send_message(cid, "Задача не найдена.", message_thread_id=tid)
        bot.answer_callback_query(cb.id)
        return

    # на всякий случай
    bot.answer_callback_query(cb.id)

if __name__=='__main__':
    bot.infinity_polling()