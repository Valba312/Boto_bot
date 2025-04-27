import requests
import time
from db import get_connection
from db import create_tasks_table, add_task, update_task_status, get_all_tasks

TOKEN = '7752152586:AAHhH9iNwhEgdwlCn9jwFrUeJZ0eszuSOIo'
URL = f'https://api.telegram.org/bot{TOKEN}'

offset = 0
user_states = {}
user_task_data = {}

# Инициализация базы данных при старте
create_tasks_table()

def get_all_message_ids(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT message_id FROM tasks WHERE chat_id = ?', (chat_id,))
    message_ids = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row[0] for row in message_ids]

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
                user_id = message['from']['id']
                user_name = message['from'].get('first_name', 'Пользователь')
                text = message.get('text', '')

                if user_id in user_states:
                    state = user_states[user_id]

                    if state == 'waiting_for_text':
                        user_task_data[user_id] = {'text': text, 'author': user_name}
                        task = user_task_data[user_id]

                        # Отправка сообщения с задачей
                        task_text = f"**Задача:**\n{task['text']}\n**Поставил:** {task['author']}\n**Статус:** ❗️Не выполнено"
                        send_resp = requests.post(f'{URL}/sendMessage', json={
                            'chat_id': chat_id,
                            'text': task_text,
                            'parse_mode': 'Markdown',
                            'reply_markup': {
                                'inline_keyboard': [
                                    [{'text': 'Взять в работу', 'callback_data': 'in_progress'}],
                                    [{'text': 'Выполнено', 'callback_data': 'completed'}]
                                ]
                            }
                        })

                        # Сохранение задачи в базу данных
                        message_id = send_resp.json()['result']['message_id']
                        add_task(chat_id, message_id, task['author'], task['text'], 'не выполнено')

                        user_states.pop(user_id)
                        user_task_data.pop(user_id)

                elif text == '/newtask':
                    user_states[user_id] = 'waiting_for_text'
                    requests.post(f'{URL}/sendMessage', json={
                        'chat_id': chat_id,
                        'text': 'Введите текст задачи:'
                    })

                elif text == '/task':
                    tasks = get_all_tasks(chat_id)
                    if not tasks:
                        requests.post(f'{URL}/sendMessage', json={
                            'chat_id': chat_id,
                            'text': 'Нет задач для отображения.'
                        })
                    else:
                        for task in tasks:
                            message_id, task_text, status = task
                            # Сохраняем message_id задачи в callback_data
                            requests.post(f'{URL}/sendMessage', json={
                                'chat_id': chat_id,
                                'text': f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n{task_text}\nСтатус: {status}\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯",
                                'parse_mode': 'Markdown',
                                'reply_markup': {
                                    'inline_keyboard': [
                                        [{
                                            'text': 'Ответить',
                                            'callback_data': f'reply_{message_id}'
                                        }]
                                    ]
                                }
                            })

            elif callback: # Одиночный блок обработки callback
                chat_id = callback['message']['chat']['id']
                data_callback = callback['data']

                if data_callback.startswith('reply_'):
                    original_message_id = int(data_callback.split('_')[1])

                    # Отправка сообщения с реплаем
                    requests.post(f'{URL}/sendMessage', json={
                        'chat_id': chat_id,
                        'text': '⚫ Точка для возврата',
                        'reply_to_message_id': original_message_id,
                    })

                    # Обязательно отвечаем на callback
                    requests.post(f'{URL}/answerCallbackQuery', json={
                        'callback_query_id': callback['id'],
                        'text': 'Ответ привязан к задаче'
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

    time.sleep(1)