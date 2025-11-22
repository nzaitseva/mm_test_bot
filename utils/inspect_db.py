import sqlite3
import json
import os


def inspect_database():
	"""Просмотр всей базы данных в удобочитаемом формате"""

	# Путь к базе данных
	db_path = "data/tests.db"
	if not os.path.exists(db_path):
		db_path = "tests.db"

	if not os.path.exists(db_path):
		print("❌ База данных не найдена!")
		return

	print(f"🔍 Анализ базы данных: {db_path}")
	print("=" * 60)

	conn = sqlite3.connect(db_path)
	cursor = conn.cursor()

	# Получаем список всех таблиц
	cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
	tables = cursor.fetchall()

	print("\n📊 ТАБЛИЦЫ В БАЗЕ:")
	for table in tables:
		print(f"  - {table[0]}")

	# Особенно детально смотрим таблицу tests
	print("\n" + "=" * 60)
	print("🧪 ДЕТАЛЬНЫЙ АНАЛИЗ ТАБЛИЦЫ TESTS:")
	print("=" * 60)

	cursor.execute("SELECT * FROM tests")
	tests = cursor.fetchall()

	# Получаем названия колонок
	cursor.execute("PRAGMA table_info(tests)")
	columns = [column[1] for column in cursor.fetchall()]

	for i, test in enumerate(tests):
		print(f"\n📝 ТЕСТ #{i + 1}:")
		print("-" * 40)

		for col_name, value in zip(columns, test):
			if col_name == 'options':
				print(f"  {col_name}:")
				try:
					options = json.loads(value)
					for opt_key, opt_value in options.items():
						print(f"    '{opt_key}' -> '{opt_value}'")
				except Exception as e:
					print(f"    ❌ Ошибка парсинга JSON: {e}")
					print(f"    📄 Сырые данные: {value}")
			else:
				print(f"  {col_name}: {value}")

	# Также смотрим таблицу schedule
	print("\n" + "=" * 60)
	print("📅 АНАЛИЗ ТАБЛИЦЫ SCHEDULE:")
	print("=" * 60)

	cursor.execute("SELECT * FROM schedule")
	schedules = cursor.fetchall()

	if schedules:
		cursor.execute("PRAGMA table_info(schedule)")
		schedule_columns = [column[1] for column in cursor.fetchall()]

		for i, schedule in enumerate(schedules):
			print(f"\n⏰ РАСПИСАНИЕ #{i + 1}:")
			print("-" * 30)
			for col_name, value in zip(schedule_columns, schedule):
				print(f"  {col_name}: {value}")
	else:
		print("  Нет записей в расписании")

	# Показываем настройки
	print("\n" + "=" * 60)
	print("⚙️  НАСТРОЙКИ:")
	print("=" * 60)

	cursor.execute("SELECT * FROM settings")
	settings = cursor.fetchall()
	for key, value in settings:
		print(f"  {key}: {value}")

	# Показываем администраторов
	print("\n" + "=" * 60)
	print("👑 АДМИНИСТРАТОРЫ:")
	print("=" * 60)

	cursor.execute("SELECT * FROM admins")
	admins = cursor.fetchall()
	for admin in admins:
		print(f"  ID: {admin[0]}, Добавлен: {admin[1]}")

	conn.close()

	print("\n" + "=" * 60)
	print("✅ Анализ завершен!")


if __name__ == "__main__":
	inspect_database()