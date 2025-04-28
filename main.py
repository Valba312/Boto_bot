import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import db

TOKEN = '8081090023:AAHizaGHTAshsYhPi7dOePK_slGyPnxQDxU'
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

<<<<<<< HEAD
# FSM-словарь
=======
# Клавиатура для статусов
STATUS_KB = {
    'inline_keyboard': [
        [{'text': 'Не выполнено',        'callback_data': 'status_не выполнено'}],
        [{'text': 'Взято в работу',      'callback_data': 'status_взято в работу'}],
        [{'text': 'Выполнено',           'callback_data': 'status_выполнено'}],
    ]
}

# Клавиатура для задач «взять/завершить»
TASK_ACTION_KB = {
    'inline_keyboard': [
        [{'text': 'Взять в работу',      'callback_data': 'in_progress'}],
        [{'text': 'Выполнено',           'callback_data': 'completed'}],
    ]
}

# Кнопка “Назад” к списку статусов
BACK_TO_STATUS_KB = {
    'inline_keyboard': [
        [{'text': '◀️ Назад', 'callback_data': 'back_to_status'}]
    ]
}

offset = 0
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e
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

<<<<<<< HEAD
# /newtask
@bot.message_handler(commands=['newtask'])
def cmd_newtask(m):
    user_states[m.from_user.id] = 'await_text'
    bot.send_message(m.chat.id, "Введите текст задачи:", message_thread_id=m.message_thread_id)
=======
            if message:
                chat_id = message['chat']['id']
                thread_id = message.get('message_thread_id')
                user_id = message['from']['id']
                user_name = message['from'].get('first_name', 'Пользователь')
                text = message.get('text', '')
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e

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

<<<<<<< HEAD
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
=======
                        payload = {
                            'chat_id': chat_id,
                            'text': (f"**Задача:**\n{task['text']}\n"
                                    f"**Поставил:** {task['author']}\n"
                                    f"**Статус:** ❗️Не выполнено"),
                            'parse_mode': 'Markdown',
                        }
                        if thread_id is not None:
                            payload['message_thread_id'] = thread_id
                        
                        payload['reply_markup'] = TASK_ACTION_KB

                        send_resp = requests.post(f'{URL}/sendMessage', json=payload)

                        message_id = send_resp.json()['result']['message_id']
                        add_task(chat_id, thread_id, message_id, task['author'], task['text'], 'не выполнено')
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e

@bot.callback_query_handler(func=lambda cb: True)
def cb_handler(cb):
    cid = cb.message.chat.id
    tid = cb.message.message_thread_id
    data = cb.data

<<<<<<< HEAD
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
=======
                elif text == '/newtask':
                    user_states[user_id] = 'waiting_for_text'
                    payload = {
                        'chat_id': chat_id,
                        'text': 'Введите текст задачи:'
                    }

                    if thread_id is not None:
                        payload['message_thread_id'] = thread_id
                    requests.post(f'{URL}/sendMessage', json=payload)

                elif text == '/task':
                    thread_id = message.get('message_thread_id')
                    task_ids = get_all_tasks(chat_id, thread_id)
                    if not task_ids:
                        payload = {
                            'chat_id': chat_id,
                            'text': 'Нет задач для отображения в этой теме.'
                        }

                        if thread_id is not None:
                            payload['message_thread_id'] = thread_id
                        requests.post(f'{URL}/sendMessage', json=payload)
                    else:
                        for msg_id in task_ids:
                            fwd_payload = {
                                'chat_id': chat_id,
                                'from_chat_id': chat_id,
                                'message_id': msg_id
                            }
                            if thread_id is not None:
                                fwd_payload['message_thread_id'] = thread_id

                            requests.post(f'{URL}/forwardMessage', json=fwd_payload)

                elif text == '/filter':
                    payload = {
                        'chat_id': chat_id,
                        'text': 'Выберите статус задач:',
                        'reply_markup': STATUS_KB
                    }
                    if thread_id is not None:
                        payload['message_thread_id'] = thread_id
                    requests.post(f'{URL}/sendMessage', json=payload)

            elif callback: # Одиночный блок обработки callback
                chat_id = callback['message']['chat']['id']
                callback_message_id = callback['message']['message_id']  # ID сообщения с кнопкой
                thread_id = callback['message'].get('message_thread_id')
                data_callback = callback['data']

                # Обработка фильтрации по статусу
                if data_callback.startswith('status_'):
                    status = data_callback.split('_')[1]
                    tasks = get_tasks_by_status(chat_id, thread_id, status)
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e

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

<<<<<<< HEAD
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
=======
                        # Редактируем текущее сообщение с кнопками
                        requests.post(f'{URL}/editMessageText', json={
                            'chat_id': chat_id,
                            'message_id': callback_message_id,  # Используем ID сообщения с кнопкой
                            'text': f'📋 Задачи со статусом "{status}":',
                            'reply_markup': {
                                'inline_keyboard': [
                                    *task_buttons,
                                    *BACK_TO_STATUS_KB['inline_keyboard']
                                ]
                            }
                        })
                    else:
                        requests.post(f'{URL}/editMessageText', json={
                            'chat_id': chat_id,
                            'message_id': callback_message_id,
                            'text': f'❌ Задачи со статусом "{status}" не найдены',
                            'reply_markup': BACK_TO_STATUS_KB
                        })
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e

    # на всякий случай
    bot.answer_callback_query(cb.id)

<<<<<<< HEAD
if __name__=='__main__':
    bot.infinity_polling()
=======
                # Обработка кнопки "Назад"
                elif data_callback == 'back_to_status':
                    requests.post(f'{URL}/editMessageText', json={
                        'chat_id': chat_id,
                        'message_id': callback_message_id,
                        'text': 'Выберите статус задач:',
                        'reply_markup': {
                            'inline_keyboard': [
                                [{'text': 'Не выполнено', 'callback_data': 'status_не выполнено'}],
                                [{'text': 'Взято в работу', 'callback_data': 'status_взято в работу'}],
                                [{'text': 'Выполнено', 'callback_data': 'status_выполнено'}]
                            ]
                        }
                    })

                elif data_callback == 'in_progress':
                    message_id = callback['message']['message_id']
                    new_text = callback['message']['text'].replace('Не выполнено', 'Взято в работу ✅')
                    requests.post(f'{URL}/editMessageText', json={
                        'chat_id': chat_id,
                        'message_id': message_id,
                        'text': new_text,
                        'parse_mode': 'Markdown',
                        'reply_markup': {
                            'inline_keyboard': [
                                [{'text': 'Выполнено', 'callback_data': 'completed'}]
                            ]
                        }
                    })
                    # Обновление статуса в базе данных
                    update_task_status(chat_id, message_id, 'взято в работу')
                    requests.post(f'{URL}/answerCallbackQuery', json={'callback_query_id': callback['id']})

                elif data_callback == 'completed':
                    message_id = callback['message']['message_id']
                    new_text = callback['message']['text']
                    new_text = new_text.replace('Не выполнено', 'Выполнено ✅').replace('Взято в работу ✅', 'Выполнено ✅')
                    requests.post(f'{URL}/editMessageText', json={
                        'chat_id': chat_id,
                        'message_id': message_id,
                        'text': new_text,
                        'parse_mode': 'Markdown'
                    })
                    # Обновление статуса в базе данных
                    update_task_status(chat_id, message_id, 'выполнено')
                    requests.post(f'{URL}/answerCallbackQuery', json={'callback_query_id': callback['id']})

                elif data_callback.startswith('reply_'):
                    original_message_id = int(data_callback.split('_')[1])

                    # Отправка сообщения с реплаем
                    requests.post(f'{URL}/sendMessage', json={
                        'chat_id': chat_id,
                        'text': '⚫ Точка для ответа',
                        'reply_to_message_id': original_message_id,
                    })

                    # Обязательно отвечаем на callback
                    requests.post(f'{URL}/answerCallbackQuery', json={
                        'callback_query_id': callback['id'],
                        'text': 'Ответ привязан к задаче'
                    })

                elif data_callback.startswith('back_'):
                    original_message_id = int(data_callback.split('_')[1])

                    # Можно просто отправить сообщение с реплаем
                    requests.post(f'{URL}/sendMessage', json={
                        'chat_id': chat_id,
                        'text': 'Возврат к задаче:',
                        'reply_to_message_id': original_message_id
                    })

                # Обязательно отвечаем на ВСЕ callback-запросы
                requests.post(f'{URL}/answerCallbackQuery', json={
                    'callback_query_id': callback['id']
                })

    time.sleep(1)
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e
