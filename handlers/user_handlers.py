from aiogram import Router, F, types
from utils.database import Database
from keyboards.keyboards import get_test_options_keyboard
import json
from utils.emoji import Emoji as E

router = Router()
db = Database()


# Отправка теста в канал
async def send_test_to_channel(test_id, channel_id, bot):
	test = db.get_test(test_id)
	if not test:
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

	keyboard = get_test_options_keyboard(test_data['options'])

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
		print(f"Ошибка отправки теста: {e}")
		return False


# Обработчик нажатий на варианты ответов
@router.callback_query(F.data.startswith("answer_"))
async def handle_test_answer(callback: types.CallbackQuery):
	try:
		option_text = callback.data.replace("answer_", "")

		tests = db.get_all_tests()
		result_text = None

		for test_id, _ in tests:
			test = db.get_test(test_id)
			if test:
				options = json.loads(test[6])
				if option_text in options:
					result_text = options[option_text]
					break

		if result_text:
			alert_text = result_text[:200]
			await callback.answer(alert_text, show_alert=True)
		else:
			await callback.answer(f"{E.ERROR} Результат не найден", show_alert=True)

	except Exception as e:
		await callback.answer(f"{E.ERROR} Произошла ошибка", show_alert=True)