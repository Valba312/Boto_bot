import sqlite3
from config import DB_PATH

# Открываем соединение с базой
DB = sqlite3.connect(DB_PATH, check_same_thread=False)

# Включаем WAL (write-ahead logging) для безопасности и параллельной работы
DB.execute('PRAGMA journal_mode=WAL;')

def get_db():
    return DB
