import requests
import time

TOKEN = '7752152586:AAHhH9iNwhEgdwlCn9jwFrUeJZ0eszuSOIo'
URL = f'https://api.telegram.org/bot{TOKEN}'

offset = 0
user_states = {}  # здесь будем хранить в каком этапе находится пользователь
user_task_data = {}  # сюда будем складывать временные данные задачи

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

                        # Публикуем задачу в чат
                        task_text = f"**Задача:**\n{task['text']}\n**Поставил:** {task['author']}\n**Статус:** ❗️Не выполнено"
                        requests.post(f'{URL}/sendMessage', json={
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

                        user_states.pop(user_id)
                        user_task_data.pop(user_id)

                elif text == '/newtask':
                    user_states[user_id] = 'waiting_for_text'
                    requests.post(f'{URL}/sendMessage', json={
                        'chat_id': chat_id,
                        'text': 'Введите текст задачи:'
                    })

            elif callback:
                chat_id = callback['message']['chat']['id']
                message_id = callback['message']['message_id']
                data_callback = callback['data']

                if data_callback == 'in_progress':
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
                    requests.post(f'{URL}/answerCallbackQuery', json={'callback_query_id': callback['id']})

                elif data_callback == 'completed':
                    new_text = callback['message']['text']
                    new_text = new_text.replace('Не выполнено', 'Выполнено ✅').replace('Взято в работу ✅', 'Выполнено ✅')
                    requests.post(f'{URL}/editMessageText', json={
                        'chat_id': chat_id,
                        'message_id': message_id,
                        'text': new_text,
                        'parse_mode': 'Markdown'
                    })
                    requests.post(f'{URL}/answerCallbackQuery', json={'callback_query_id': callback['id']})

    time.sleep(1)