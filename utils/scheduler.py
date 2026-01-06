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
		# Получаем текущее время в UTC для сравнения
		now_utc = datetime.now(pytz.utc)

		all_schedules = self.db.get_active_schedules()

		for schedule_id, test_id, channel_id, test_title in all_schedules:
			# Получаем запланированное время из базы (оно хранится в UTC)
			# scheduled_time stored as ISO string in DB via Database.add_schedule
			try:
				scheduled_time_str = self._get_schedule_time(schedule_id)
				scheduled_time_utc = datetime.fromisoformat(scheduled_time_str).replace(tzinfo=pytz.utc)
			except Exception:
				logger.exception("Failed to parse scheduled_time for schedule_id=%s", schedule_id)
				continue

			# Сравниваем с текущим временем в UTC
			if now_utc >= scheduled_time_utc:
				try:
					success = await send_test_to_channel(test_id, channel_id, self.bot)

					if success:
						self.db.mark_schedule_sent(schedule_id)
						logger.info(f"{E.CONFIRM} Тест '{test_title}' отправлен в {channel_id}")
					else:
						logger.info(f"{E.ERROR} Ошибка отправки теста '{test_title}' в {channel_id}")

				except Exception as e:
					logger.info(f"{E.ERROR} Ошибка отправки теста: {e}")

	def _get_schedule_time(self, schedule_id):
		rows = self.db._exec('SELECT scheduled_time FROM schedule WHERE id = ?', (int(schedule_id),), fetchone=True)
		return rows[0] if rows else None

	async def start_scheduler(self):
		while True:
			await self.check_pending_schedules()
			await asyncio.sleep(30)