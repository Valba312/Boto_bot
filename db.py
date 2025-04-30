import sqlite3

DB = sqlite3.connect('tasks.db', check_same_thread=False)
DB.execute('PRAGMA journal_mode=WAL;')

def create_tables():
    DB.execute('''
      CREATE TABLE IF NOT EXISTS tasks (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id      INTEGER NOT NULL,
        thread_id    INTEGER,
        message_id   INTEGER NOT NULL,
        author       TEXT    NOT NULL,
        text         TEXT    NOT NULL,
        status       TEXT    NOT NULL,
        accepted_by  TEXT
      )
    ''')
    DB.commit()

def add_task(chat_id, thread_id, message_id, author, text, status, accepted_by):
    DB.execute('''
      INSERT INTO tasks
        (chat_id, thread_id, message_id, author, text, status, accepted_by)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, thread_id, message_id, author, text, status, accepted_by))
    DB.commit()

def update_task_status(chat_id, thread_id, message_id, status, accepted_by):
    DB.execute('''
      UPDATE tasks
         SET status = ?, accepted_by = ?
       WHERE chat_id = ? AND thread_id IS ? AND message_id = ?
    ''', (status, accepted_by, chat_id, thread_id, message_id))
    DB.commit()

def get_all_tasks(chat_id, thread_id):
    cur = DB.cursor()
    cur.execute('''
      SELECT message_id
        FROM tasks
       WHERE chat_id = ? AND thread_id IS ?
    ''', (chat_id, thread_id))
    return [row[0] for row in cur.fetchall()]

def get_tasks_by_status(chat_id, thread_id, status):
    cur = DB.cursor()
    cur.execute('''
      SELECT message_id
        FROM tasks
       WHERE chat_id = ? AND thread_id IS ? AND status = ?
    ''', (chat_id, thread_id, status))
    return [row[0] for row in cur.fetchall()]

def get_task_by_id(chat_id, thread_id, message_id):
    cur = DB.cursor()
    cur.execute('''
      SELECT author, text, status, accepted_by
        FROM tasks
       WHERE chat_id = ? AND thread_id IS ? AND message_id = ?
    ''', (chat_id, thread_id, message_id))
    return cur.fetchone()