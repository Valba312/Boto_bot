import sqlite3

<<<<<<< HEAD
DB = sqlite3.connect('tasks.db', check_same_thread=False)
DB.execute('PRAGMA journal_mode=WAL;')

def create_tables():
    c = DB.cursor()
    c.execute('''
      CREATE TABLE IF NOT EXISTS tasks (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id           INTEGER NOT NULL,
        thread_id         INTEGER,
        message_id        INTEGER NOT NULL,
        author            TEXT    NOT NULL,
        text              TEXT    NOT NULL,
        status            TEXT    NOT NULL
      )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_thread_status ON tasks(thread_id, status)')
    DB.commit()

def add_task(chat_id, thread_id, message_id, author, text, status):
    DB.execute(
      'INSERT INTO tasks(chat_id,thread_id,message_id,author,text,status) VALUES(?,?,?,?,?,?)',
      (chat_id, thread_id, message_id, author, text, status)
    )
    DB.commit()
=======
# Единое глобальное соединение
_conn = sqlite3.connect('tasks.db', check_same_thread=False)
# Режим Write-Ahead Logging для более быстрой параллельной работы
_conn.execute('PRAGMA journal_mode=WAL;')

def get_connection():
    return _conn

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
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_thread_status
      ON tasks(message_thread_id, status)
    ''')
    
    conn.commit()
    cursor.close()

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
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e

def update_task_status(chat_id, message_id, status):
<<<<<<< HEAD
    DB.execute(
      'UPDATE tasks SET status = ? WHERE chat_id = ? AND message_id = ?',
      (status, chat_id, message_id)
    )
    DB.commit()

def get_all_tasks(chat_id, thread_id):
    cur = DB.cursor()
    if thread_id is None:
        cur.execute('SELECT message_id FROM tasks WHERE chat_id=? AND thread_id IS NULL', (chat_id,))
    else:
        cur.execute('SELECT message_id FROM tasks WHERE chat_id=? AND thread_id=?', (chat_id, thread_id))
    return [r[0] for r in cur.fetchall()]

def get_tasks_by_status(chat_id, thread_id, status):
    cur = DB.cursor()
    if thread_id is None:
        cur.execute('SELECT message_id FROM tasks WHERE chat_id=? AND thread_id IS NULL AND status=?',
                    (chat_id, status))
    else:
        cur.execute('SELECT message_id FROM tasks WHERE chat_id=? AND thread_id=? AND status=?',
                    (chat_id, thread_id, status))
    return [r[0] for r in cur.fetchall()]

def get_task_by_id(chat_id, message_id):
    cur = DB.cursor()
    cur.execute('SELECT text,status FROM tasks WHERE chat_id=? AND message_id=?', (chat_id, message_id))
    return cur.fetchone()
=======
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE tasks
    SET status = ?
    WHERE chat_id = ? AND message_id = ?
    ''', (status, chat_id, message_id))
    conn.commit()
    cursor.close()

def get_all_tasks(chat_id, thread_id):
    conn = get_connection()
    cursor = conn.cursor()
    if thread_id is None:
        cursor.execute('''
            SELECT message_id, text, status
            FROM tasks 
            WHERE chat_id = ? AND message_thread_id IS NULL
            ''', (chat_id,))
    else:
        cursor.execute('''
            SELECT message_id, text, status
            FROM tasks 
            WHERE chat_id = ? AND message_thread_id = ?
            ''', (chat_id, thread_id))
    tasks = cursor.fetchall()
    cursor.close()
    return [r[0] for r in tasks]

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
    return task
>>>>>>> b3b8df740b1c720581fd5202c96f27223d647f5e
