import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List


class SimpleDB:
    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            # Таблица пользователей
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    max_id INTEGER PRIMARY KEY,
                    fullname TEXT,
                    phone TEXT,
                    pyrus_user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица заявок
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    max_id INTEGER NOT NULL,
                    pyrus_task_id INTEGER,
                    status TEXT DEFAULT 'Новая',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY (max_id) REFERENCES users(max_id)
                )
            ''')

            # Индексы
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tickets_max ON tickets(max_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_users_pyrus ON users(pyrus_user_id)')

