import os
import logging

from utils.database import Database

logger = logging.getLogger(__name__)

def reset_database():
	# Удаляем существующую базу данных
	if os.path.exists("../tests.db"):
		os.remove("../tests.db")
		logger.info("🗑️ Старая база данных удалена")

	# Создаем новую
	db = Database()
	logger.info("✅ Новая база данных создана")


if __name__ == "__main__":
	reset_database()