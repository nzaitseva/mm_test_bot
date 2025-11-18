import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from utils.database import Database
from keyboards.keyboards import *
from states import TestCreation, ScheduleCreation, TestDeletion, ScheduleDeletion
from utils.emoji import Emoji as E
from utils.channel_utils import parse_channel_input  # Добавляем импорт
import json
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

router = Router()
db = Database()


@router.message(Command("admin"))
async def admin_start(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} пытается зайти в админку")  # временно
    if not db.is_admin(message.from_user.id):
        logger.info("Не админ")  # временно
        await message.answer(f"{E.CANCEL} У вас нет прав администратора")
        return

    await message.answer(
        f"{E.HAND} Добро пожаловать в панель администратора!\n"
        "Здесь вы можете создавать тесты и планировать их отправку в каналы.",
        reply_markup=get_admin_main_menu()
    )

# Список тестов
@router.message(F.text == f"{E.LIST} Мои тесты")
async def show_my_tests(message: types.Message):
	if not db.is_admin(message.from_user.id):
		return

	tests = db.get_all_tests()
	if not tests:
		await message.answer(f"{E.POST_BOX} У вас пока нет созданных тестов")
		return

	text = f"{E.LIST} Ваши тесты:\n\n"
	for test_id, title in tests:
		text += f"{E.STAPLE} {title} (ID: {test_id})\n"

	await message.answer(text)


### Шаги для добавления теста

@router.message(F.text == f"{E.CREATE} Создать тест")
async def start_test_creation(message: types.Message, state: FSMContext):
	if not db.is_admin(message.from_user.id):
		return

	await state.set_state(TestCreation.waiting_for_title)
	await message.answer(
		"Введите название теста:",
		reply_markup=get_cancel_keyboard()
	)

# Название
@router.message(TestCreation.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
	if message.text == f"{E.CANCEL} Отмена":
		await state.clear()
		await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
		return

	await state.update_data(title=message.text)
	await state.set_state(TestCreation.waiting_for_content_type)
	await message.answer("Выберите тип контента:", reply_markup=get_content_type_keyboard())

# Тип сообщения (текст, фото, текст + фото)
@router.callback_query(TestCreation.waiting_for_content_type, F.data.startswith("content_"))
async def process_content_type(callback: types.CallbackQuery, state: FSMContext):
	content_type = callback.data.replace("content_", "")
	await state.update_data(content_type=content_type)

	if content_type in ["text", "both"]:
		await state.set_state(TestCreation.waiting_for_text_content)
		await callback.message.answer("Введите текстовое содержание теста:", reply_markup=get_cancel_keyboard())
	else:
		await state.set_state(TestCreation.waiting_for_photo)
		await callback.message.answer("Отправьте картинку для теста:", reply_markup=get_cancel_keyboard())

	await callback.answer()

# Текст
@router.message(TestCreation.waiting_for_text_content)
async def process_text_content(message: types.Message, state: FSMContext):
	if message.text == f"{E.CANCEL} Отмена":
		await state.clear()
		await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
		return

	await state.update_data(text_content=message.text)
	data = await state.get_data()

	if data['content_type'] == 'text':
		await state.set_state(TestCreation.waiting_for_question)
		await message.answer("Введите вопрос теста:", reply_markup=get_cancel_keyboard())
	else:
		await state.set_state(TestCreation.waiting_for_photo)
		await message.answer("Теперь отправьте картинку:", reply_markup=get_cancel_keyboard())

# Добавление фото
@router.message(TestCreation.waiting_for_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
	if message.text == f"{E.CANCEL} Отмена":
		await state.clear()
		await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
		return

	photo_file_id = message.photo[-1].file_id
	await state.update_data(photo_file_id=photo_file_id)

	data = await state.get_data()
	if data['content_type'] == 'photo' or 'text_content' in data:
		await state.set_state(TestCreation.waiting_for_question)
		await message.answer("Введите вопрос теста:", reply_markup=get_cancel_keyboard())

# Вопрос
@router.message(TestCreation.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
	if message.text == f"{E.CANCEL} Отмена":
		await state.clear()
		await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
		return

	await state.update_data(question=message.text)
	await state.set_state(TestCreation.waiting_for_options)
	await message.answer(
		f"{E.TEXT} Введите варианты ответов в формате:\n"
		"Вариант1 :: Результат1 (до 200 символов)\n"
		"Вариант2 :: Результат2 (до 200 символов)\n\n"
		f"{E.LAMP} Пример:\n"
		"Волны :: Ваше настроение переменчиво. Внутри есть эмоции, которые требуют выхода.\n"
		"Дерево :: Вы чувствуете стабильность и укорененность в жизни.\n"
		"Пламя :: Вы полны энергии и страсти! Направьте её в нужное русло.",
		reply_markup=get_cancel_keyboard()
	)

# Вариантоы ответов
@router.message(TestCreation.waiting_for_options)
async def process_options(message: types.Message, state: FSMContext):
	if message.text == f"{E.CANCEL} Отмена":
		await state.clear()
		await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
		return

	try:
		options = {}
		lines = message.text.split('\n')
		# парсим варианты ответа вида "Вариант1 :: Результат 1"
		for line in lines:
			if '::' in line:
				option, result = line.split('::', 1)
				option_text = option.strip()
				result_text = result.strip()

				if len(result_text) > 200:
					await message.answer(
						f"{E.ERROR} Результат для '{option_text}' слишком длинный ({len(result_text)} символов). "
						f"Максимум 200 символов. Пожалуйста, введите варианты заново:"
					)
					return

				options[option_text] = result_text

		if len(options) < 2:
			await message.answer(f"{E.ERROR} Нужно как минимум 2 варианта ответа. Попробуйте еще раз:")
			return

		data = await state.get_data()
		test_id = db.add_test(
			title=data['title'],
			content_type=data['content_type'],
			text_content=data.get('text_content', ''),
			photo_file_id=data.get('photo_file_id', ''),
			question_text=data['question'],
			options=options
		)

		await message.answer(
			f"{E.SUCCESS} Тест '{data['title']}' успешно создан!\n"
			f"{E.TEST} ID теста: {test_id}\n"
			f"{E.DARTS} Вариантов ответа: {len(options)}",
			reply_markup=get_admin_main_menu()
		)
		await state.clear()

	except Exception as e:
		await message.answer(f"{E.CANCEL} Ошибка: {e}\nПопробуйте еще раз:")


###  Планирование отправки

@router.message(F.text == f"{E.CALENDAR} Запланировать отправку")
async def start_scheduling(message: types.Message, state: FSMContext):
	if not db.is_admin(message.from_user.id):
		return

	tests = db.get_all_tests()
	if not tests:
		await message.answer(f"{E.ERROR} Сначала создайте тест")
		return

	await state.set_state(ScheduleCreation.waiting_for_test_selection)
	await message.answer(
		"Выберите тест для отправки:",
		reply_markup=get_tests_list_keyboard(tests)
	)

# Выбор теста
@router.callback_query(ScheduleCreation.waiting_for_test_selection, F.data.startswith("select_test_"))
async def process_test_selection(callback: types.CallbackQuery, state: FSMContext):
	test_id = int(callback.data.replace("select_test_", ""))
	await state.update_data(test_id=test_id)
	await state.set_state(ScheduleCreation.waiting_for_channel)
	await callback.message.answer(
		"Введите ID или @username канала (например: @my_channel или -1001234567890):",
		reply_markup=get_cancel_keyboard()
	)
	await callback.answer()

# Выбор канала (@channel_name или https://t.me/channel_name)
@router.message(ScheduleCreation.waiting_for_channel)
async def process_channel(message: types.Message, state: FSMContext):
	if message.text == f"{E.CANCEL} Отмена":
		await state.clear()
		await message.answer(f"{E.CANCEL} Планирование отменено", reply_markup=get_admin_main_menu())
		return

	# Преобразуем ввод канала в стандартный формат
	channel_id = parse_channel_input(message.text)
	await state.update_data(channel_id=channel_id)
	await state.set_state(ScheduleCreation.waiting_for_time)
	await message.answer(
		f"{E.CHANNEL} Канал распознан как: <code>{channel_id}</code>\n\n"
		f"{E.CLOCK} Введите время отправки в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
		"Например: 25.12.2024 15:30",
		parse_mode="HTML",
		reply_markup=get_cancel_keyboard()
	)

# Время отправки теста
@router.message(ScheduleCreation.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
	if message.text == f"{E.CANCEL} Отмена":
		await state.clear()
		await message.answer(f"{E.CANCEL} Планирование отменено", reply_markup=get_admin_main_menu())
		return
	try:
		# Получаем часовой пояс из настроек
		timezone_str = db.get_timezone()
		tz = pytz.timezone(timezone_str)

		# Парсим введенное время (считаем, что оно в установленном часовом поясе)
		local_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")

		# Локализуем время в указанном часовом поясе
		localized_time = tz.localize(local_time)

		# Конвертируем в UTC для хранения
		utc_time = localized_time.astimezone(pytz.utc)

		data = await state.get_data()
		db.add_schedule(data['test_id'], data['channel_id'], utc_time)

		test = db.get_test(data['test_id'])
		test_title = test[1] if test else "Неизвестный тест"

		await message.answer(
			f"{E.CONFIRM} Тест '{test_title}' запланирован!\n"
			f"{E.CALENDAR} Дата: {local_time.strftime('%d.%m.%Y %H:%M')} ({timezone_str})\n"
			f"{E.CHANNEL} Канал: {data['channel_id']}",
			reply_markup=get_admin_main_menu()
		)
		await state.clear()

	except ValueError:
		await message.answer(
			f"{E.ERROR} Неверный формат времени. Используйте: ДД.ММ.ГГГГ ЧЧ:ММ\n"
			f"Пример: 25.12.2024 15:30"
		)


### Управление расписаниями отправки

@router.message(F.text == f"{E.SCHEDULES} Активные расписания")
async def show_active_schedules(message: types.Message):
	if not db.is_admin(message.from_user.id):
		return

	schedules = db.get_active_schedules()
	if not schedules:
		await message.answer(f"{E.POST_BOX} Нет активных расписаний")
		return

	# Получаем часовой пояс для отображения
	timezone_str = db.get_timezone()
	tz = pytz.timezone(timezone_str)

	text = f"{E.SCHEDULES} Активные расписания ({timezone_str}):\n\n"
	for schedule_id, test_title, channel_id, scheduled_time in schedules:
		try:
			# Преобразуем UTC время из базы в локальный часовой пояс
			utc_time = datetime.fromisoformat(scheduled_time).replace(tzinfo=pytz.utc)
			local_time = utc_time.astimezone(tz)
			formatted_time = local_time.strftime("%d.%m.%Y %H:%M")
		except:
			formatted_time = scheduled_time

		text += f"{E.STAPLE} {test_title}\n  {E.CALENDAR} {formatted_time}\n  {E.CHANNEL} {channel_id}\n\n"
	await message.answer(
		text + "Нажмите на расписание чтобы удалить его:",
		reply_markup=get_schedules_list_keyboard(schedules)
	)

@router.callback_query(F.data.startswith("delete_schedule_"))
async def process_schedule_selection_for_deletion(callback: types.CallbackQuery, state: FSMContext):
	schedule_id = int(callback.data.replace("delete_schedule_", ""))

	# Получаем информацию о расписании
	schedules = db.get_active_schedules()
	schedule_info = None
	for s in schedules:
		if s[0] == schedule_id:
			schedule_info = s
			break

	if schedule_info:
		schedule_id, test_title, channel_id, scheduled_time = schedule_info
		try:
			time_obj = datetime.fromisoformat(scheduled_time)
			formatted_time = time_obj.strftime("%d.%m.%Y %H:%M")
		except:
			formatted_time = scheduled_time

		await state.update_data(
			schedule_id=schedule_id,
			test_title=test_title,
			channel_id=channel_id,
			scheduled_time=formatted_time
		)

		await state.set_state(ScheduleDeletion.waiting_for_confirmation)
		await callback.message.answer(
			f"{E.WARNING}️ Вы уверены, что хотите удалить расписание?\n\n"
			f"Тест: <b>{test_title}</b>\n"
			f"Канал: {channel_id}\n"
			f"Время: {formatted_time}",
			parse_mode="HTML",
			reply_markup=get_confirmation_keyboard(action="delete_schedule")
		)

	await callback.answer()

@router.callback_query(ScheduleDeletion.waiting_for_confirmation, F.data == "confirm_delete_schedule")
async def confirm_schedule_deletion(callback: types.CallbackQuery, state: FSMContext):
	data = await state.get_data()
	schedule_id = data.get('schedule_id')
	test_title = data.get('test_title')

	if schedule_id:
		success = db.delete_schedule(schedule_id)

		if success:
			await callback.message.edit_text(
				f"{E.CONFIRM} Расписание для теста «{test_title}» успешно удалено!"
			)
		else:
			await callback.message.edit_text(
				f"{E.ERROR} Произошла ошибка при удалении расписания"
			)

	await state.clear()
	await callback.answer()

@router.callback_query(ScheduleDeletion.waiting_for_confirmation, F.data == "cancel_delete")
async def cancel_schedule_deletion(callback: types.CallbackQuery, state: FSMContext):
	await state.clear()
	await callback.message.edit_text(f"{E.CANCEL} Удаление расписания отменено")
	await callback.answer()


### Удаление тестов

# Обработчик  для проверки активных расписаний
@router.callback_query(TestDeletion.waiting_for_test_selection, F.data.startswith("delete_test_"))
async def process_test_selection_for_deletion(callback: types.CallbackQuery, state: FSMContext):
	test_id = int(callback.data.replace("delete_test_", ""))

	# Проверяем, есть ли активные расписания
	if db.has_active_schedules(test_id):
		await callback.answer(
			f"{E.ERROR} Нельзя удалить тест с активными расписаниями! "
			"Сначала удалите расписания через меню «Активные расписания».",
			show_alert=True
		)
		return

	# Сохраняем ID теста в состоянии
	await state.update_data(test_id=test_id)

	# Получаем информацию о тесте для подтверждения
	test = db.get_test(test_id)
	if test:
		test_title = test[1]
		await state.set_state(TestDeletion.waiting_for_confirmation)
		await callback.message.answer(
			f"{E.WARNING}️ Вы уверены, что хотите удалить тест:\n\n"
			f"<b>«{test_title}»</b>\n\n"
			f"Это действие нельзя отменить!",
			parse_mode="HTML",
			reply_markup=get_confirmation_keyboard()
		)

	await callback.answer()

@router.message(F.text == f"{E.DELETE} Удалить тест")
async def start_test_deletion(message: types.Message, state: FSMContext):
	if not db.is_admin(message.from_user.id):
		return

	tests = db.get_all_tests()
	if not tests:
		await message.answer(f"{E.POST_BOX} У вас пока нет созданных тестов для удаления")
		return

	await state.set_state(TestDeletion.waiting_for_test_selection)
	await message.answer(
		"Выберите тест для удаления:",
		reply_markup=get_tests_list_keyboard(tests, action="delete")
	)

@router.callback_query(TestDeletion.waiting_for_confirmation, F.data == "confirm_delete")
async def confirm_test_deletion(callback: types.CallbackQuery, state: FSMContext):
	data = await state.get_data()
	test_id = data.get('test_id')

	if test_id:
		test = db.get_test(test_id)
		if test:
			test_title = test[1]
			success = db.delete_test(test_id)

			if success:
				await callback.message.edit_text(
					f"{E.CONFIRM} Тест «{test_title}» успешно удален!"
				)
			else:
				await callback.message.edit_text(
					f"{E.ERROR} Произошла ошибка при удалении теста «{test_title}»"
				)

	await state.clear()
	await callback.answer()

@router.callback_query(TestDeletion.waiting_for_confirmation, F.data == "cancel_delete")
async def cancel_test_deletion(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(f"{E.CANCEL} Удаление отменено")
    await callback.answer()


# Обработчик для тестирования
@router.message(Command("test_channel"))
async def test_channel_parser(message: types.Message):
	"""Тестовая команда для проверки парсера каналов"""
	if not db.is_admin(message.from_user.id):
		return

	test_cases = [
		"https://t.me/channel_name",
		"http://t.me/channel_name",
		"t.me/channel_name",
		"@channel_name",
		"channel_name",
		"-1001234567890",
		"https://t.me/joinchat/ABCDEF"
	]

	result_text = "🔍 Тест парсера каналов:\n\n"
	for test_case in test_cases:
		parsed = parse_channel_input(test_case)
		result_text += f"<code>{test_case}</code> → <code>{parsed}</code>\n"
	await message.answer(result_text, parse_mode="HTML")
