import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
	os.makedirs('logs', exist_ok=True)

	formatter = logging.Formatter(
		'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S'
	)

	file_handler = RotatingFileHandler(
		'logs/bot.log',
		maxBytes=10 * 1024 * 1024,  # 10 MB
		backupCount=5,
		encoding='utf-8'
	)
	file_handler.setFormatter(formatter)
	file_handler.setLevel(logging.INFO)

	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	console_handler.setLevel(logging.INFO)

	# Root logger
	logging.basicConfig(
		level=logging.INFO,
		handlers=[file_handler, console_handler]
	)

	# Устанавливаем уровень логирования для библиотек
	logging.getLogger('aiogram').setLevel(logging.WARNING)
	logging.getLogger('apscheduler').setLevel(logging.WARNING)

	logger = logging.getLogger(__name__)
	logger.info("✅ Логирование настроено")

	return logger


# Создаем логгер для этого модуля (на всякий случай)
logger = logging.getLogger(__name__)