import sqlite3

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

def update_task_status(chat_id, message_id, status):
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