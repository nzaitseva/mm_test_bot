import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.admin_handlers import router as admin_router
from handlers.user_handlers import router as user_router
from handlers.settings_handlers import router as settings_router
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
		db = Database("data/tests.db")

		# Добавление администраторов
		for admin_id in ADMIN_IDS:
			if not db.is_admin(admin_id):
				success = db.add_admin(admin_id)
				if success:
					logger.info(f"{E.SUCCESS} Администратор {admin_id} добавлен")

		# Регистрация роутеров
		dp.include_router(admin_router)
		dp.include_router(user_router)
		dp.include_router(settings_router)
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