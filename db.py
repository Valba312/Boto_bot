import sqlite3

# Подключение к базе
def get_connection():
    return sqlite3.connect('tasks.db')

# Создание таблицы задач
def create_tasks_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        message_thread_id INTEGER,
        message_id INTEGER NOT NULL,
        author TEXT NOT NULL,
        text TEXT NOT NULL,
        status TEXT NOT NULL
    )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Добавление новой задачи
def add_task(chat_id, thread_id, message_id, author, text, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO tasks (chat_id, message_thread_id, message_id, author, text, status)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (chat_id, thread_id, message_id, author, text, status))
    conn.commit()
    cursor.close()
    conn.close()

# Обновление статуса задачи
def update_task_status(chat_id, message_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE tasks
    SET status = ?
    WHERE chat_id = ? AND message_id = ?
    ''', (status, chat_id, message_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_tasks(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT message_id, text, status 
    FROM tasks 
    WHERE chat_id = ?
    ''', (chat_id,))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return tasks

def get_tasks_by_status(chat_id, thread_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    if thread_id is None:
        cursor.execute('''
            SELECT message_id FROM tasks 
            WHERE chat_id = ? AND message_thread_id is NULL AND status = ?
            ''', (chat_id, status))
    else:
        cursor.execute('''
            SELECT message_id FROM tasks 
            WHERE chat_id = ? AND message_thread_id = ? AND status = ?
            ''', (chat_id, thread_id, status))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row[0] for row in tasks]

def get_task_by_message_id(chat_id, message_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT message_id, text, status 
    FROM tasks 
    WHERE chat_id = ? AND message_id = ?
    ''', (chat_id, message_id))
    task = cursor.fetchone()
    cursor.close()
    conn.close()
    return task
