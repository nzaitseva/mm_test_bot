import json
import logging

from aiogram import Router, F, types

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
		logger.error(f"❌ Тест {test_id} не найден для отправки в канал {channel_id}")
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
	logger.info(f"🛠️ Отправка теста {test_id} в канал {channel_id}")
	logger.info(f"🛠️ Варианты ответов: {list(test_data['options'].keys())}")

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
		logger.info(f"Ошибка отправки теста: {e}")
		return False


@router.callback_query(F.data.startswith("answer_"))
async def handle_test_answer(callback: types.CallbackQuery):
	try:
		callback_data = callback.data
		logger.info(f"📨 Получен callback_data: {callback_data}")

		# Поддерживаем оба формата:
		# Старый: "answer_Вариант"
		# Новый: "answer_ТЕСТ_ID_Вариант"

		parts = callback_data.split('_', 2)  # разделяем максимум на 3 части
		logger.info(f"🔍 Разделенные части: {parts}")

		test_id = None
		option_text = None

		if len(parts) == 3:  # Новый формат: answer_3_Машина
			try:
				test_id = int(parts[1])
				option_text = parts[2]
				logger.info(f"🔍 Новый формат: test_id={test_id}, option_text='{option_text}'")
			except ValueError:
				# Если не удалось преобразовать test_id, пробуем старый формат
				test_id = None
				option_text = parts[1] + ('_' + parts[2] if len(parts) > 2 else '')
				logger.info(f"🔍 Смешанный формат, option_text='{option_text}'")

		elif len(parts) == 2:  # Старый формат: answer_Машина
			option_text = parts[1]
			logger.info(f"🔍 Старый формат: option_text='{option_text}'")
		else:
			logger.error(f"❌ Неизвестный формат callback_data: {callback_data}")
			await callback.answer(f"{E.ERROR} Ошибка данных", show_alert=True)
			return

		# Если есть test_id - ищем в конкретном тесте
		if test_id is not None:
			test = db.get_test(test_id)
			if not test:
				logger.error(f"❌ Тест с ID {test_id} не найден")
				await callback.answer(f"{E.ERROR} Тест не найден", show_alert=True)
				return

			options = json.loads(test[6])
			logger.info(f"🔍 Поиск в тесте {test_id}: {list(options.keys())}")

			if option_text in options:
				result_text = options[option_text]
				logger.info(f"✅ Найден результат: '{result_text}'")

				if result_text and result_text.strip():
					alert_text = result_text[:200]
					await callback.answer(alert_text, show_alert=True)
				else:
					await callback.answer(
						f"{E.INFO} Для этого варианта результат пока не настроен",
						show_alert=True
					)
			else:
				logger.warning(f"⚠️ Вариант '{option_text}' не найден в тесте {test_id}")
				await callback.answer(f"{E.ERROR} Вариант ответа не найден", show_alert=True)

		else:
			# Старый формат: ищем во всех активных тестах
			logger.info(f"🔍 Поиск '{option_text}' во всех тестах")
			tests = db.get_all_tests()
			result_text = None
			found_in_test = None

			for test_id, _ in tests:
				test = db.get_test(test_id)
				if test and test[7]:  # проверяем is_active = 1
					options = json.loads(test[6])
					if option_text in options:
						candidate_result = options[option_text]
						# Берем первый НЕ ПУСТОЙ результат
						if candidate_result and candidate_result.strip():
							result_text = candidate_result
							found_in_test = test_id
							break
						# Если нашли пустой результат, продолжаем поиск
						elif result_text is None:  # сохраняем первый найденный (даже пустой)
							result_text = candidate_result
							found_in_test = test_id

			if result_text is not None:
				logger.info(f"✅ Найден в тесте {found_in_test}: '{result_text}'")
				if result_text and result_text.strip():
					alert_text = result_text[:200]
					await callback.answer(alert_text, show_alert=True)
				else:
					await callback.answer(f"{E.INFO} Результат пустой", show_alert=True)
			else:
				logger.warning(f"⚠️ Вариант '{option_text}' не найден ни в одном тесте")
				await callback.answer(f"{E.ERROR} Результат не найден", show_alert=True)

	except Exception as e:
		logger.error(f"❌ Ошибка в обработчике ответов: {e}")
		# Не показываем alert при ошибке, т.к. callback уже мог быть обработан
		try:
			await callback.answer(f"{E.ERROR} Произошла ошибка", show_alert=True)
		except:
			pass  # Игнорируем ошибку, если callback уже обработан