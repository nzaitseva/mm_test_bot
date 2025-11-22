import json
import logging

from aiogram import Router, F, types
from aiogram.filters import Command

from utils.database import Database
from keyboards.keyboards import get_test_options_keyboard
from utils.emoji import Emoji as E

logger = logging.getLogger(__name__)

router = Router()
db = Database()


# Отправка теста в канал
async def send_test_to_channel(test_id, channel_id, bot):
	test = db.get_test(test_id)
	if not test:
		logger.error(f"{E.ERROR} Тест {test_id} не найден для отправки в канал {channel_id}")
		return False

	test_data = {
		'id': test[0],
		'title': test[1],
		'content_type': test[2],
		'text_content': test[3],
		'photo_file_id': test[4],
		'question_text': test[5],
		'options': json.loads(test[6])
	}

	# Передаем test_id в клавиатуру для нового формата callback_data
	keyboard = get_test_options_keyboard(test_data['options'], test_data['id'])

	try:
		if test_data['content_type'] == 'text':
			await bot.send_message(
				chat_id=channel_id,
				text=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['text_content']}\n\n{test_data['question_text']}",
				reply_markup=keyboard
			)
		elif test_data['content_type'] == 'photo':
			await bot.send_photo(
				chat_id=channel_id,
				photo=test_data['photo_file_id'],
				caption=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['question_text']}",
				reply_markup=keyboard
			)
		elif test_data['content_type'] == 'both':
			await bot.send_photo(
				chat_id=channel_id,
				photo=test_data['photo_file_id'],
				caption=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['text_content']}\n\n{test_data['question_text']}",
				reply_markup=keyboard
			)
		return True
	except Exception as e:
		logger.error(f"{E.ERROR} Ошибка отправки теста {test_id} в {channel_id}: {e}")
		return False


# Обработчик нажатий на варианты ответов (ТОЛЬКО НОВЫЙ ФОРМАТ)
@router.callback_query(F.data.startswith("test_"))
async def handle_test_answer(callback: types.CallbackQuery):
	try:
		# Формат: test_ТЕСТ_ID_option_ВАРИАНТ_ТЕКСТ
		parts = callback.data.split('_', 3)  # test, ID, option, ТЕКСТ
		#logger.info(f"📨 Получен callback_data: {callback.data}")
		#logger.info(f"🔍 Разделенные части: {parts}")

		if len(parts) != 4 or parts[0] != "test" or parts[2] != "option":
			logger.error(f"{E.ERROR} Неверный формат: {callback.data}")
			await callback.answer(f"{E.ERROR} Ошибка данных", show_alert=True)
			return

		test_id = int(parts[1])
		option_text = parts[3]

		#logger.info(f"🔍 Поиск: test_id={test_id}, option_text='{option_text}'")

		# Ищем ТОЛЬКО в указанном тесте
		test = db.get_test(test_id)
		if not test:
			logger.error(f"{E.ERROR} Тест {test_id} не найден")
			await callback.answer(f"{E.ERROR} Тест не найден", show_alert=True)
			return

		options = json.loads(test[6])
		#logger.info(f"🔍 Варианты в тесте {test_id}: {list(options.keys())}")

		if option_text in options:
			result_text = options[option_text]
			#logger.info(f"✅ Найден результат: '{result_text}'")

			if result_text and result_text.strip():
				alert_text = result_text[:200]
				await callback.answer(alert_text, show_alert=True)
			else:
				await callback.answer(
					f"{E.INFO} Для этого варианта результат пока не настроен",
					show_alert=True
				)
		else:
			logger.warning(f"{E.WARNING} Вариант '{option_text}' не найден в тесте {test_id}")
			await callback.answer(f"{E.ERROR} Вариант ответа не найден", show_alert=True)

	except Exception as e:
		logger.error(f"{E.ERROR} Ошибка в обработчике ответов: {e}")
		await callback.answer(f"{E.ERROR} Произошла ошибка", show_alert=True)


