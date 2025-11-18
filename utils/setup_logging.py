import logging
import os
from logging.handlers import RotatingFileHandler

from utils.emoji import Emoji as E


# Логи пишутся в файл и выводятся в консоль

def setup_logging():

	os.makedirs('logs', exist_ok=True)

	formatter = logging.Formatter(
		'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S'
	)

	# Хендлер для файла с ротацией
	file_handler = RotatingFileHandler(
		'logs/bot.log',
		maxBytes=10 * 1024 * 1024,  # 10 MB
		backupCount=5,
		encoding='utf-8'
	)
	file_handler.setFormatter(formatter)
	file_handler.setLevel(logging.INFO)

	# Хендлер для консоли
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	console_handler.setLevel(logging.INFO)

	# Корневой логгер
	logging.basicConfig(
		level=logging.INFO,
		handlers=[file_handler, console_handler]
	)

	# Уровень логирования для библиотек
	logging.getLogger('aiogram').setLevel(logging.WARNING)
	logging.getLogger('apscheduler').setLevel(logging.WARNING)

	logger = logging.getLogger(__name__)
	logger.info(f"{E.SUCCESS} Логирование настроено")

	return logger