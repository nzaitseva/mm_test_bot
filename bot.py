import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.admin import router as admin_router
from handlers.user_handlers import router as user_router
from handlers.settings_handlers import router as settings_router
from handlers.debug_router import router as debug_router
from utils.database import Database
from utils.scheduler import SchedulerManager
from utils.setup_logging import setup_logging
from utils.emoji import Emoji as E
from utils.config import load_config

# Load config with bot token and admin IDs
config = load_config()
logger = setup_logging()


async def main():
	if not config.bot_token:
		logger.error(f"{E.ERROR} BOT_TOKEN not found")
		return

	db = Database()
	bot = Bot(token=config.bot_token)
	storage = MemoryStorage()
	dp = Dispatcher(storage=storage)

	try:
		for admin_id in config.admin_ids:
			db.add_admin(admin_id)
		logger.info(f"{E.INFO} Admins set: {config.admin_ids}")

		dp.include_router(user_router)
		dp.include_router(settings_router)
		dp.include_router(admin_router)
		dp.include_router(debug_router)

		scheduler = SchedulerManager(bot)
		asyncio.create_task(scheduler.start_scheduler())

		logger.info(f"{E.ROCKET} Bot started (2026)")

		# Pass `db` to start_polling
		# Now db is available in all handlers as argument `db: Database`
		await dp.start_polling(bot, db=db)

	except Exception as e:
		logger.exception(f"{E.ERROR} Critical error: {e}")
		raise
	finally:
		await storage.close()
		await bot.session.close()
		if hasattr(db, 'close'):
			await db.close()
		logger.info(f"{E.STOPPED} Bot stopped")


if __name__ == "__main__":
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		pass
