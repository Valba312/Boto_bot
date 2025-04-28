import requests
import time
from db import get_connection
from db import create_tasks_table, add_task, update_task_status, get_all_tasks, get_tasks_by_status, get_task_by_message_id

TOKEN = '7752152586:AAHhH9iNwhEgdwlCn9jwFrUeJZ0eszuSOIo'
URL = f'https://api.telegram.org/bot{TOKEN}'

offset = 0
user_states = {}
user_task_data = {}

# Инициализация базы данных при старте
create_tasks_table()

while True:
    response = requests.get(f'{URL}/getUpdates', params={'timeout': 100, 'offset': offset})
    data = response.json()

    if data['ok']:
        for update in data['result']:
            offset = update['update_id'] + 1

            message = update.get('message')
            callback = update.get('callback_query')

            if message:
                chat_id = message['chat']['id']
                thread_id = message.get('message_thread_id')
                user_id = message['from']['id']
                user_name = message['from'].get('first_name', 'Пользователь')
                text = message.get('text', '')

                if user_id in user_states:
                    state = user_states[user_id]

                    if state == 'waiting_for_text':
                        user_task_data[user_id] = {'text': text, 'author': user_name}
                        task = user_task_data[user_id]

                        payload = {
                            'chat_id': chat_id,
                            'text': f"**Задача:**\n{task['text']}\n"
                                    f"**Поставил:** {task['author']}\n"
                                    f"**Статус:** ❗️Не выполнено",
                            'parse_mode': 'Markdown',
                            'reply_markup': {
                                'inline_keyboard': [
                                    [{'text': 'Взять в работу', 'callback_data': 'in_progress'}],
                                    [{'text': 'Выполнено',       'callback_data': 'completed'}]
                                ]
                            }
                        }
                        if thread_id is not None:
                            payload['message_thread_id'] = thread_id

                        send_resp = requests.post(f'{URL}/sendMessage', json=payload)

                        message_id = send_resp.json()['result']['message_id']
                        add_task(chat_id, thread_id, message_id, task['author'], task['text'], 'не выполнено')

                        user_states.pop(user_id)
                        user_task_data.pop(user_id)

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
                        'reply_markup': {
                            'inline_keyboard': [
                                [{'text': 'Не выполнено',    'callback_data': 'status_не выполнено'}],
                                [{'text': 'Взято в работу',  'callback_data': 'status_взято в работу'}],
                                [{'text': 'Выполнено',       'callback_data': 'status_выполнено'}]
                            ]
                        }
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

                    if tasks:
                        task_buttons = []
                        for task_id in tasks:
                            task = get_task_by_message_id(chat_id, task_id)
                            if task:
                                task_text_short = task[1][:20] + '...' if len(task[1]) > 20 else task[1]
                                task_buttons.append([{
                                    'text': f'📌 {task_text_short}', 
                                    'callback_data': f'task_{task_id}_{status}'
                                }])

                        # Редактируем текущее сообщение с кнопками
                        requests.post(f'{URL}/editMessageText', json={
                            'chat_id': chat_id,
                            'message_id': callback_message_id,  # Используем ID сообщения с кнопкой
                            'text': f'📋 Задачи со статусом "{status}":',
                            'reply_markup': {
                                'inline_keyboard': [
                                    *task_buttons,
                                    [{'text': '◀️ Назад', 'callback_data': 'back_to_status'}]
                                ]
                            }
                        })
                    else:
                        requests.post(f'{URL}/editMessageText', json={
                            'chat_id': chat_id,
                            'message_id': callback_message_id,
                            'text': f'❌ Задачи со статусом "{status}" не найдены',
                            'reply_markup': {
                                'inline_keyboard': [
                                    [{'text': '◀️ Назад', 'callback_data': 'back_to_status'}]
                                ]
                            }
                        })

                # Обработка выбора задачи
                elif data_callback.startswith('task_'):
                    task_id = int(data_callback.split('_')[1])
                    status = data_callback.split('_')[2]
                    task = get_task_by_message_id(chat_id, task_id)
                    
                    if task:
                        # Отправляем новое сообщение с реплаем
                        requests.post(f'{URL}/sendMessage', json={
                            'chat_id': chat_id,
                            'text': f'🔍 Выбранная задача:\n\n{task[1]}\n\nСтатус: {status}',
                            'reply_to_message_id': task_id,  # Реплай к оригинальной задаче
                            'reply_markup': {
                                'inline_keyboard': [
                                    [{'text': '◀️ Назад к списку', 'callback_data': f'status_{status}'}]
                                ]
                            }
                        })
                    else:
                        requests.post(f'{URL}/sendMessage', json={
                            'chat_id': chat_id,
                            'text': '❌ Задача не найдена'
                        })

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
