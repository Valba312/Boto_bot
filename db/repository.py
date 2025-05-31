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

    # ⬇ Обязательно создаём кэш
    create_cache_table()
    return True

@_with_retry
def create_cache_table():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS message_cache (
            message_id INTEGER PRIMARY KEY,
            chat_id INTEGER NOT NULL,
            last_checked TIMESTAMP NOT NULL
        )
    ''')
    db.commit()

@_with_retry
def get_cached_message_ids(expiry_seconds=600):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT message_id FROM message_cache
         WHERE strftime('%s', 'now') - strftime('%s', last_checked) < ?
    ''', (expiry_seconds,))
    return set(row[0] for row in cur.fetchall())

@_with_retry
def update_cache(chat_id, message_id):
    db = get_db()
    db.execute('''
        INSERT INTO message_cache (message_id, chat_id, last_checked)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(message_id) DO UPDATE SET last_checked=CURRENT_TIMESTAMP
    ''', (message_id, chat_id))
    db.commit()

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
def get_task_by_id(chat_id, thread_id, message_id):
    db = get_db()
    cur = db.cursor()
    cur.execute('''
        SELECT author, text, status, accepted_by
          FROM tasks
         WHERE chat_id = ? AND thread_id IS ? AND message_id = ?
    ''', (chat_id, thread_id, message_id))
    return cur.fetchone()

@_with_retry
def get_tasks(chat_id=None, thread_id=None, status=None, full=False):
    """
    Универсальная функция:
    - Возвращает задачи по фильтру chat_id, thread_id, status
    - Если full=True → [{'chat_id': ..., 'message_id': ...}]
    - Иначе → [message_id, message_id, ...]
    """
    db = get_db()
    cur = db.cursor()

    query = "SELECT chat_id, message_id FROM tasks"
    conditions = []
    params = []

    if chat_id is not None:
        conditions.append("chat_id = ?")
        params.append(chat_id)
    if thread_id is not None:
        conditions.append("thread_id IS ?")
        params.append(thread_id)
    if status is not None:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cur.execute(query, tuple(params))

    if full:
        return [{"chat_id": row[0], "message_id": row[1]} for row in cur.fetchall()]
    else:
        return [row[1] for row in cur.fetchall()]

@_with_retry
def delete_task_by_message_id(message_id):
    """
    Удаляет задачу из базы данных по message_id.
    Возвращает True, если что-то было удалено.
    """
    db = get_db()
    db.execute("DELETE FROM tasks WHERE message_id = ?", (message_id,))
    db.commit()
    return db.total_changes > 0