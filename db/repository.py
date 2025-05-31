import sqlite3
import logging
import time
from db import get_db

logger = logging.getLogger(__name__)

# Настройки автоматического повтора при блокировке базы
RETRY_COUNT = 3     # сколько раз пробовать снова
RETRY_DELAY = 0.2   # пауза между попытками в секундах

def _with_retry(func):
    """
    Декоратор для автоматического повторения функции, если база занята (database is locked).
    Возвращает строку-код ошибки или результат функции.
    """
    def wrapper(*args, **kwargs):
        for attempt in range(RETRY_COUNT):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if 'database is locked' in str(e):
                    logger.warning(f"[{func.__name__}] database is locked, попытка {attempt+1}/{RETRY_COUNT}")
                    time.sleep(RETRY_DELAY)
                else:
                    logger.error(f"[{func.__name__}] sqlite3.OperationalError: {e}")
                    break
            except sqlite3.IntegrityError as e:
                logger.warning(f"[{func.__name__}] Нарушение ограничений: {e}")
                return "integrity"
            except sqlite3.DatabaseError as e:
                logger.error(f"[{func.__name__}] DatabaseError: {e}", exc_info=True)
                return "db_error"
            except Exception as e:
                logger.exception(f"[{func.__name__}] Неизвестная ошибка: {e}")
                return "unknown"
        logger.error(f"[{func.__name__}] Не удалось выполнить после {RETRY_COUNT} попыток из-за 'database is locked'")
        return "locked"
    return wrapper

@_with_retry
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
    return True

@_with_retry
def add_task(chat_id, thread_id, message_id, author, text, status, accepted_by):
    db = get_db()
    db.execute('''
        INSERT INTO tasks
            (chat_id, thread_id, message_id, author, text, status, accepted_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, thread_id, message_id, author, text, status, accepted_by))
    db.commit()
    return True

@_with_retry
def update_task_status(chat_id, thread_id, message_id, status, accepted_by):
    db = get_db()
    db.execute('''
        UPDATE tasks
           SET status = ?, accepted_by = ?
         WHERE chat_id = ? AND thread_id IS ? AND message_id = ?
    ''', (status, accepted_by, chat_id, thread_id, message_id))
    db.commit()
    return True

@_with_retry
def get_all_tasks(chat_id, thread_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT message_id
          FROM tasks
         WHERE chat_id = ? AND thread_id IS ?
    ''', (chat_id, thread_id))
    return [row[0] for row in cur.fetchall()]

@_with_retry
def get_tasks_by_status(chat_id, thread_id, status):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT message_id
          FROM tasks
         WHERE chat_id = ? AND thread_id IS ? AND status = ?
    ''', (chat_id, thread_id, status))
    return [row[0] for row in cur.fetchall()]

@_with_retry
def get_task_by_id(chat_id, thread_id, message_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT author, text, status, accepted_by
          FROM tasks
         WHERE chat_id = ? AND thread_id IS ? AND message_id = ?
    ''', (chat_id, thread_id, message_id))
    return cur.fetchone()

# ✅ Новая функция — удаление задачи по message_id
@_with_retry
def delete_task_by_message_id(message_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE message_id = ?", (message_id,))
    db.commit()
    return db.total_changes > 0