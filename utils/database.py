import sqlite3
import json
import logging

from datetime import datetime
from typing import List, Tuple, Optional


logger = logging.getLogger(__name__)

class Database:
	def __init__(self, db_path="tests.db"):
		self.db_path = db_path
		self.init_db()

	def init_db(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()

		# Таблица настроек
		cursor.execute('''
	        CREATE TABLE IF NOT EXISTS settings (
	            key TEXT PRIMARY KEY,
	            value TEXT NOT NULL
	        )
	    ''')

		# Таблица администраторов
		cursor.execute('''
	        CREATE TABLE IF NOT EXISTS admins (
	            user_id INTEGER PRIMARY KEY,
	            added_at DATETIME DEFAULT CURRENT_TIMESTAMP
	        )
	    ''')

		# Таблица тестов (включая локальный путь photo_path)
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

		# Таблица расписания
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

		# Часовой пояс по умолчанию (UTC) если его еще нет
		cursor.execute(
			'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
			('timezone', 'UTC')
		)

		conn.commit()
		conn.close()

	# Настройки
	def get_all_settings(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute('SELECT key, value FROM settings')
		settings = cursor.fetchall()
		conn.close()
		return dict(settings)

	def get_setting(self, key: str, default: str = None) -> str:
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
		result = cursor.fetchone()
		conn.close()
		return result[0] if result else default

	def set_setting(self, key: str, value: str) -> bool:
		try:
			conn = sqlite3.connect(self.db_path)
			cursor = conn.cursor()
			cursor.execute(
				'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
				(key, value)
			)
			conn.commit()
			conn.close()
			return True
		except Exception as e:
			logger.info(f"Ошибка при сохранении настройки: {e}")
			return False

	def get_timezone(self) -> str:
		return self.get_setting('timezone', 'UTC')

	def set_timezone(self, timezone: str) -> bool:
		return self.set_setting('timezone', timezone)

	def is_admin(self, user_id):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (int(user_id),))
		result = cursor.fetchone() is not None
		conn.close()
		return result

	def add_admin(self, user_id):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		try:
			cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (int(user_id),))
			conn.commit()
		except Exception as e:
			logger.info(f"Ошибка при добавлении администратора: {e}")
			conn.rollback()
		finally:
			conn.close()

	def add_test(self, title: str, content_type: str, text_content: Optional[str],
				 photo_file_id: Optional[str], photo_path: Optional[str], question_text: str, options: dict) -> int:
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute('''
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
		))
		test_id = cursor.lastrowid
		conn.commit()
		conn.close()
		return test_id

	# Помечает просто как неактивный
	# TODO: сделать удаление насовсем
	def delete_test(self, test_id):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		try:
			cursor.execute('UPDATE tests SET is_active = 0 WHERE id = ?', (int(test_id),))
			conn.commit()
			return True
		except Exception as e:
			logger.info(f"Ошибка при удалении теста: {e}")
			conn.rollback()
			return False
		finally:
			conn.close()

	def get_test(self, test_id):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		# Явно выбираем поля в порядке: id, title, content_type, text_content, photo_file_id, photo_path, question_text, options, created_at, is_active
		cursor.execute('''
			SELECT id, title, content_type, text_content, photo_file_id, photo_path, question_text, options, created_at, is_active
			FROM tests WHERE id = ?
		''', (int(test_id),))
		test = cursor.fetchone()
		conn.close()
		return test

	def get_all_tests(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute('SELECT id, title FROM tests WHERE is_active = 1')
		tests = cursor.fetchall()
		conn.close()
		return tests

	def add_schedule(self, test_id: int, channel_id: str, scheduled_time: datetime) -> bool:
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute('''
            INSERT INTO schedule (test_id, channel_id, scheduled_time)
            VALUES (?, ?, ?)
        ''', (int(test_id), str(channel_id), scheduled_time.isoformat()))
		conn.commit()
		conn.close()

	# Проверяет, есть ли активные расписания перед удалением
	def has_active_schedules(self, test_id):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute(
			'SELECT COUNT(*) FROM schedule WHERE test_id = ? AND is_sent = 0',
			(int(test_id),)
		)
		count = cursor.fetchone()[0]
		conn.close()
		return count > 0

	def get_active_schedules(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		cursor.execute('''
            SELECT s.id, t.title, s.channel_id, s.scheduled_time 
            FROM schedule s 
            JOIN tests t ON s.test_id = t.id 
            WHERE s.is_sent = 0
            ORDER BY s.scheduled_time
        ''')
		schedules = cursor.fetchall()
		conn.close()
		return schedules

	def delete_schedule(self, schedule_id):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		try:
			cursor.execute('DELETE FROM schedule WHERE id = ?', (int(schedule_id),))
			conn.commit()
			return True
		except Exception as e:
			logger.info(f"Ошибка при удалении расписания: {e}")
			conn.rollback()
			return False
		finally:
			conn.close()

	def update_test(self, test_id: int, **fields) -> bool:
		"""
		Обновить поля теста. Поддерживаемые ключи:
		title, content_type, text_content, photo_file_id, photo_path, question_text, options (dict или JSON-строка), is_active
		"""
		if not fields:
			return False

		allowed = {'title', 'content_type', 'text_content', 'photo_file_id', 'photo_path', 'question_text', 'options', 'is_active'}
		update_parts = []
		values = []
		for k, v in fields.items():
			if k not in allowed:
				continue
			# Если options — dict, сериализуем
			if k == 'options' and isinstance(v, dict):
				v = json.dumps(v, ensure_ascii=False)
			# Преобразуем булевые is_active в 0/1 если нужно
			if k == 'is_active' and isinstance(v, bool):
				v = 1 if v else 0
			update_parts.append(f"{k} = ?")
			values.append(v)
		if not update_parts:
			return False

		values.append(int(test_id))
		sql = f"UPDATE tests SET {', '.join(update_parts)} WHERE id = ?"
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()
		try:
			cursor.execute(sql, tuple(values))
			conn.commit()
			return True
		except Exception as e:
			logger.info(f"Ошибка при обновлении теста {test_id}: {e}")
			conn.rollback()
			return False
		finally:
			conn.close()