import sqlite3
import json
import logging
import os

from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str = "tests.db"):
        self.db_path = db_path
        # ensure directory exists if path contains directories
        if os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    # context manager for connection - callers should use with self.connect() as conn:
    def connect(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL,
                text_content TEXT,
                photo_file_id TEXT,
                photo_path TEXT,
                question_text TEXT NOT NULL,
                options TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER,
                channel_id TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                is_sent BOOLEAN DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES tests (id)
            )
        ''')

        cursor.execute(
            'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
            ('timezone', 'UTC')
        )

        conn.commit()
        conn.close()

    # helpers
    def _exec(self, sql: str, params: tuple = (), fetchone=False, fetchall=False, commit=False):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            if commit:
                conn.commit()
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
        except Exception as e:
            logger.exception(f"DB error for query: {sql} params={params} -> {e}")
            raise
        finally:
            conn.close()

    # small helper to save photo via existing utility (kept here for convenience)
    async def _save_photo_helper(self, message) -> str:
        from utils.photo_manager import save_photo_from_message
        return await save_photo_from_message(message)

    # Settings
    def get_all_settings(self):
        rows = self._exec('SELECT key, value FROM settings', fetchall=True)
        return dict(rows) if rows else {}

    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        row = self._exec('SELECT value FROM settings WHERE key = ?', (key,), fetchone=True)
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> bool:
        try:
            self._exec('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value), commit=True)
            return True
        except Exception as e:
            logger.exception(f"Failed to set setting {key}={value}: {e}")
            return False

    def get_timezone(self) -> str:
        return self.get_setting('timezone', 'UTC')

    def set_timezone(self, timezone: str) -> bool:
        return self.set_setting('timezone', timezone)

    # Admins
    def is_admin(self, user_id):
        row = self._exec('SELECT 1 FROM admins WHERE user_id = ?', (int(user_id),), fetchone=True)
        return row is not None

    def add_admin(self, user_id):
        try:
            self._exec('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (int(user_id),), commit=True)
            return True
        except Exception as e:
            logger.exception(f"Ошибка при добавлении администратора: {e}")
            return False

    # Tests
    def add_test(self, title: str, content_type: str, text_content: Optional[str],
                 photo_file_id: Optional[str], photo_path: Optional[str], question_text: str, options: dict) -> int:
        self._exec('''
            INSERT INTO tests (title, content_type, text_content, photo_file_id, photo_path, question_text, options)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(title),
            str(content_type),
            str(text_content) if text_content else None,
            str(photo_file_id) if photo_file_id else None,
            str(photo_path) if photo_path else None,
            str(question_text),
            json.dumps(options, ensure_ascii=False)
        ), commit=True)
        # lastrowid requires opening connection; fetch last inserted id
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT last_insert_rowid()')
        last_id = cursor.fetchone()[0]
        conn.close()
        return last_id

    def update_test(self, test_id: int, **fields) -> bool:
        if not fields:
            return False

        allowed = {'title', 'content_type', 'text_content', 'photo_file_id', 'photo_path', 'question_text', 'options', 'is_active'}
        update_parts = []
        values = []
        for k, v in fields.items():
            if k not in allowed:
                continue
            if k == 'options' and isinstance(v, dict):
                v = json.dumps(v, ensure_ascii=False)
            if k == 'is_active' and isinstance(v, bool):
                v = 1 if v else 0
            update_parts.append(f"{k} = ?")
            values.append(v)
        if not update_parts:
            return False

        values.append(int(test_id))
        sql = f"UPDATE tests SET {', '.join(update_parts)} WHERE id = ?"
        try:
            self._exec(sql, tuple(values), commit=True)
            return True
        except Exception as e:
            logger.exception(f"Ошибка при обновлении теста {test_id}: {e}")
            return False

    def delete_test(self, test_id):
        try:
            self._exec('UPDATE tests SET is_active = 0 WHERE id = ?', (int(test_id),), commit=True)
            return True
        except Exception as e:
            logger.exception(f"Ошибка при удалении теста: {e}")
            return False

    def get_test(self, test_id):
        return self._exec('''
            SELECT id, title, content_type, text_content, photo_file_id, photo_path, question_text, options, created_at, is_active
            FROM tests WHERE id = ?
        ''', (int(test_id),), fetchone=True)

    def get_all_tests(self):
        return self._exec('SELECT id, title FROM tests WHERE is_active = 1', fetchall=True) or []

    # Schedule
    def add_schedule(self, test_id: int, channel_id: str, scheduled_time: datetime) -> bool:
        self._exec('''
            INSERT INTO schedule (test_id, channel_id, scheduled_time)
            VALUES (?, ?, ?)
        ''', (int(test_id), str(channel_id), scheduled_time.isoformat()), commit=True)
        return True

    def has_active_schedules(self, test_id):
        row = self._exec('SELECT COUNT(*) FROM schedule WHERE test_id = ? AND is_sent = 0', (int(test_id),), fetchone=True)
        return (row[0] if row else 0) > 0

    def get_active_schedules(self):
        return self._exec('''
            SELECT s.id, t.title, s.channel_id, s.scheduled_time 
            FROM schedule s 
            JOIN tests t ON s.test_id = t.id 
            WHERE s.is_sent = 0
            ORDER BY s.scheduled_time
        ''', fetchall=True) or []

    def delete_schedule(self, schedule_id):
        try:
            self._exec('DELETE FROM schedule WHERE id = ?', (int(schedule_id),), commit=True)
            return True
        except Exception as e:
            logger.exception(f"Ошибка при удалении расписания: {e}")
            return False

    # Utility: static parser for channel input (moved as static method to be reusable)
    @staticmethod
    def parse_channel_input(input_text: str) -> str:
        s = input_text.strip()
        # simple heuristics
        if s.startswith("https://t.me/") or s.startswith("http://t.me/") or s.startswith("t.me/"):
            return s.split("/")[-1] if not s.startswith("-100") else s
        return s