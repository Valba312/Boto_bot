from db import get_db

def create_tables():
    db = get_db()
    db.execute('''
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
    db.commit()

def add_task(chat_id, thread_id, message_id, author, text, status, accepted_by):
    db = get_db()
    db.execute('''
        INSERT INTO tasks
            (chat_id, thread_id, message_id, author, text, status, accepted_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, thread_id, message_id, author, text, status, accepted_by))
    db.commit()

def update_task_status(chat_id, thread_id, message_id, status, accepted_by):
    db = get_db()
    db.execute('''
        UPDATE tasks
           SET status = ?, accepted_by = ?
         WHERE chat_id = ? AND thread_id IS ? AND message_id = ?
    ''', (status, accepted_by, chat_id, thread_id, message_id))
    db.commit()

def get_all_tasks(chat_id, thread_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT message_id
          FROM tasks
         WHERE chat_id = ? AND thread_id IS ?
    ''', (chat_id, thread_id))
    return [row[0] for row in cur.fetchall()]

def get_tasks_by_status(chat_id, thread_id, status):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT message_id
          FROM tasks
         WHERE chat_id = ? AND thread_id IS ? AND status = ?
    ''', (chat_id, thread_id, status))
    return [row[0] for row in cur.fetchall()]

def get_task_by_id(chat_id, thread_id, message_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT author, text, status, accepted_by
          FROM tasks
         WHERE chat_id = ? AND thread_id IS ? AND message_id = ?
    ''', (chat_id, thread_id, message_id))
    return cur.fetchone()
