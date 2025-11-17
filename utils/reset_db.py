from utils.database import Database
import os


def reset_database():
	# Удаляем существующую базу данных
	if os.path.exists("../tests.db"):
		os.remove("../tests.db")
		print("🗑️ Старая база данных удалена")

	# Создаем новую
	db = Database()
	print("✅ Новая база данных создана")


if __name__ == "__main__":
	reset_database()