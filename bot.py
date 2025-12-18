import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.admin_handlers import router as admin_router
from handlers.user_handlers import router as user_router
from handlers.settings_handlers import router as settings_router
from handlers.debug_router import router as debug_router

from utils.database import Database
from utils.scheduler import SchedulerManager
from utils.setup_logging import setup_logging
from utils.emoji import Emoji as E

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование ПЕРВЫМ делом
logger = setup_logging()

# Конфигурация - с fallback для Docker
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]


async def main():
	if not BOT_TOKEN:
		logger.error(f"{E.ERROR} BOT_TOKEN не найден в переменных окружения")
		return

	try:
		bot = Bot(token=BOT_TOKEN)
		storage = MemoryStorage()
		dp = Dispatcher(storage=storage)

		# Инициализация базы данных с путем для Docker
		db = Database()

		# Добавление администраторов
		if ADMIN_IDS:
			logger.info(f"{E.INFO} Администраторы из окружения: {ADMIN_IDS}")
		else:
			logger.info(f"{E.WARNING} Список ADMIN_IDS пуст. Убедитесь, что в .env указаны администраторы.")

		for admin_id in ADMIN_IDS:
			if not db.is_admin(admin_id):
				success = db.add_admin(admin_id)
				if success is None:
					# add_admin в текущей реализации не возвращает True/False, просто логируем
					logger.info(f"{E.SUCCESS} Попытка добавить администратора {admin_id}")
				else:
					logger.info(f"{E.SUCCESS} Администратор {admin_id} добавлен")

		# Покажем состояние таблицы admins (полезно для отладки)
		try:
			conn_admins = db.get_all_settings()  # reusing DB method to ensure DB accessible
		except Exception:
			# просто логируем отдельно наличие админов из БД
			import sqlite3
			conn = sqlite3.connect(db.db_path)
			cur = conn.cursor()
			try:
				cur.execute("SELECT user_id, added_at FROM admins")
				admin_rows = cur.fetchall()
				logger.info(f"{E.INFO} Администраторы в БД: {admin_rows}")
			except Exception as e:
				logger.exception(f"{E.ERROR} Не удалось получить администраторов из БД: {e}")
			finally:
				conn.close()

		# Регистрация роутеров
		dp.include_router(admin_router)
		dp.include_router(user_router)
		dp.include_router(settings_router)
		dp.include_router(debug_router)
		logger.info(f"{E.SUCCESS} Все роутеры зарегистрированы")

		# Запуск планировщика в фоне
		scheduler = SchedulerManager(bot)
		asyncio.create_task(scheduler.start_scheduler())
		logger.info(f"{E.SUCCESS} Планировщик запущен")

		logger.info(f"{E.ROCKET} Бот запущен и готов к работе")

		await dp.start_polling(bot)

	except Exception as e:
		logger.error(f"{E.ERROR} Критическая ошибка при запуске бота: {e}")
		raise
	finally:
		await storage.close()
		await bot.session.close()
		logger.info(f"{E.STOPPED} Бот остановлен")


if __name__ == "__main__":
	asyncio.run(main())