import os
import asyncio
from dataclasses import dataclass
from dotenv import load_dotenv
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

# load env
#load_dotenv()
#BOT_TOKEN = os.getenv('BOT_TOKEN')
#ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]


config = load_config()

logger = setup_logging()


async def main():
    if not config.bot_token:
        logger.error(f"{E.ERROR} BOT_TOKEN not found")
        return

    try:
        bot = Bot(token=config.bot_token)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        db = Database() # TODO: почему в каждом файле свой экземпляр Database?

        # add admins from env
        for admin_id in config.admin_ids:
            db.add_admin(admin_id)
        logger.info(f"{E.INFO} Admins set: {config.admin_ids}")

        # include routers: functional routers first, debug last
        dp.include_router(user_router)
        dp.include_router(settings_router)
        dp.include_router(admin_router)
        dp.include_router(debug_router)

        # scheduler
        scheduler = SchedulerManager(bot)
        asyncio.create_task(scheduler.start_scheduler())

        logger.info(f"{E.ROCKET} Bot started")
        await dp.start_polling(bot)

    except Exception as e:
        logger.exception(f"{E.ERROR} Critical error: {e}")
        raise
    finally:
        await storage.close()
        await bot.session.close()
        logger.info(f"{E.STOPPED} Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())