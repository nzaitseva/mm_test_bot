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
	def __init__(self, bot, db_path="tests.db"):
		self.bot = bot
		self.db_path = db_path
		self.db = Database(db_path)

	async def check_pending_schedules(self):
		conn = sqlite3.connect(self.db_path)
		cursor = conn.cursor()

		# Получаем текущее время в UTC для сравнения
		now_utc = datetime.now(pytz.utc)

		cursor.execute(
			'''SELECT s.id, s.test_id, s.channel_id, t.title 
			   FROM schedule s 
			   JOIN tests t ON s.test_id = t.id 
			   WHERE s.is_sent = 0'''
		)
		all_schedules = cursor.fetchall()

		for schedule_id, test_id, channel_id, test_title in all_schedules:
			# Получаем запланированное время из базы (оно хранится в UTC)
			cursor.execute(
				'SELECT scheduled_time FROM schedule WHERE id = ?',
				(schedule_id,)
			)
			scheduled_time_str = cursor.fetchone()[0]

			# Преобразуем строку в datetime объект (предполагаем, что хранится в UTC)
			scheduled_time_utc = datetime.fromisoformat(scheduled_time_str).replace(tzinfo=pytz.utc)

			# Сравниваем с текущим временем в UTC
			if now_utc >= scheduled_time_utc:
				try:
					success = await send_test_to_channel(test_id, channel_id, self.bot)

					if success:
						cursor.execute(
							'UPDATE schedule SET is_sent = 1 WHERE id = ?',
							(schedule_id,)
						)
						conn.commit()
						logger.info(f"{E.CONFIRM} Тест '{test_title}' отправлен в {channel_id}")
					else:
						logger.info(f"{E.ERROR} Ошибка отправки теста '{test_title}' в {channel_id}")

				except Exception as e:
					logger.info(f"{E.ERROR} Ошибка отправки теста: {e}")

		conn.close()

	async def start_scheduler(self):
		while True:
			await self.check_pending_schedules()
			await asyncio.sleep(30)