import pytz
import logging
import asyncio
import sqlite3
from datetime import datetime

from handlers.user_handlers import send_test_to_channel
from utils.database import Database
from utils.emoji import Emoji as E

logger = logging.getLogger(__name__)


class SchedulerManager:
	def __init__(self, bot, db: Database):
		self.bot = bot
		self.db = db

	async def check_pending_schedules(self):
		now_utc = datetime.now(pytz.utc)

		all_schedules = await self.db.get_active_schedules()

		for schedule_id, test_title, channel_id, scheduled_time in all_schedules:
			# Use scheduled_time from the query if available, otherwise fetch from DB
			try:
				scheduled_time_str = scheduled_time
				scheduled_time_utc = datetime.fromisoformat(scheduled_time_str).replace(tzinfo=pytz.utc)
			except Exception:
				try:
					scheduled_time_str = await self._get_schedule_time(schedule_id)
					scheduled_time_utc = datetime.fromisoformat(scheduled_time_str).replace(tzinfo=pytz.utc)
				except Exception:
					logger.exception("Failed to parse scheduled_time for schedule_id=%s", schedule_id)
					continue

			if now_utc >= scheduled_time_utc:
				try:
					test_id = await self._get_schedule_test_id(schedule_id)
					if test_id is None:
						logger.error("%s Не удалось получить test_id для schedule_id=%s", E.ERROR, schedule_id)
						continue

					success = await send_test_to_channel(test_id, channel_id, self.bot, self.db)

					if success:
						await self.db.mark_schedule_sent(schedule_id)
						logger.info(f"{E.CONFIRM} Тест '{test_title}' отправлен в {channel_id}")
					else:
						logger.info(f"{E.ERROR} Ошибка отправки теста '{test_title}' в {channel_id}")

				except Exception as e:
					logger.info(f"{E.ERROR} Ошибка отправки теста: {e}")

	async def _get_schedule_time(self, schedule_id):
		rows = await self.db._exec('SELECT scheduled_time FROM schedule WHERE id = ?', (int(schedule_id),), fetchone=True)
		return rows[0] if rows else None

	async def _get_schedule_test_id(self, schedule_id):
		row = await self.db._exec('SELECT test_id FROM schedule WHERE id = ?', (int(schedule_id),), fetchone=True)
		return row[0] if row else None

	async def start_scheduler(self):
		while True:
			await self.check_pending_schedules()
			await asyncio.sleep(30)