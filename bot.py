import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.admin_handlers import router as admin_router
from handlers.user_handlers import router as user_router
from handlers.settings_handlers import router as settings_router  # Добавляем
from utils.database import Database
from utils.scheduler import SchedulerManager
from utils.emoji import Emoji as E
from utils.setup_logging import setup_logging

load_dotenv()
logger = setup_logging()


BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]


async def main():
	if not BOT_TOKEN:
		logger.error(f"{E.ERROR} BOT_TOKEN не найден")
		return

	bot = Bot(token=BOT_TOKEN)
	storage = MemoryStorage()
	dp = Dispatcher(storage=storage)

	db = Database()

	# для отладки
	current_timezone = db.get_timezone()
	logger.info(f"{E.SCHEDULES} Текущий часовой пояс: {current_timezone}")

	# Добавление администраторов по ID из настроек (если ещё не добавлены)
	for admin_id in ADMIN_IDS:
		if not db.is_admin(admin_id):
			db.add_admin(admin_id)
			logger.info(f"{E.CONFIRM} Администратор {admin_id} добавлен")

	dp.include_router(admin_router)
	dp.include_router(user_router)
	dp.include_router(settings_router)
	logger.info(f"{E.SUCCESS} Роутеры зарегистрированы")

	scheduler = SchedulerManager(bot)
	asyncio.create_task(scheduler.start_scheduler())

	logger.info("Бот запущен")

	try:
		await dp.start_polling(bot)
	finally:
		await storage.close()
		await bot.session.close()


if __name__ == "__main__":
	asyncio.run(main())