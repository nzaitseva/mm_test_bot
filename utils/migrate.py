# migrate.py
import sqlite3
from emoji import Emoji as E

def migrate_database():
	conn = sqlite3.connect('tests.db')
	cursor = conn.cursor()

	# Создаем таблицу настроек если её нет
	cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

	# Добавляем часовой пояс по умолчанию
	cursor.execute(
		'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
		('timezone', 'UTC')
	)

	conn.commit()
	conn.close()
	logger.info(f"{E.CONFIRM} Миграция базы данных завершена")


if __name__ == "__main__":
	migrate_database()