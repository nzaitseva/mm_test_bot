import sqlite3
import logging

logger = logging.getLogger(__name__)

def check_database():
	conn = sqlite3.connect('tests.db')
	cursor = conn.cursor()

	# Проверяем существование таблицы settings
	cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
	settings_table = cursor.fetchone()
	logger.info(f"Таблица settings: {'✅ Есть' if settings_table else '❌ Нет'}")

	if settings_table:
		# Проверяем настройки
		cursor.execute("SELECT * FROM settings")
		settings = cursor.fetchall()
		logger.info("Настройки в базе:")
		for key, value in settings:
			logger.info(f"  {key}: {value}")

	# Проверяем таблицу admins
	cursor.execute("SELECT * FROM admins")
	admins = cursor.fetchall()
	logger.info(f"Администраторы: {admins}")

	conn.close()


if __name__ == "__main__":
	check_database()