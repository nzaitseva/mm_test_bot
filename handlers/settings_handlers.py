import pytz
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from utils.database import Database
from keyboards.keyboards import get_settings_keyboard, get_timezone_keyboard, get_admin_main_menu
from utils.emoji import Emoji as E

router = Router()
db = Database()


# Получение настроек (для логов)
def get_settings_text():
	current_timezone = db.get_timezone()
	return (
		f"{E.SETTINGS} <b>Настройки бота</b>\n\n"
		f"📍 <b>Текущий часовой пояс:</b> {current_timezone}\n\n"
		f"Выберите настройку для изменения:"
	)


# Основной обработчик настроек
@router.message(F.text == f"{E.SETTINGS} Настройки")
async def show_settings(message: types.Message):
	if not db.is_admin(message.from_user.id):
		return

	await message.answer(
		get_settings_text(),
		parse_mode="HTML",
		reply_markup=get_settings_keyboard()
	)


# Настройки часового пояса
@router.callback_query(F.data == "settings_timezone")
async def show_timezone_settings(callback: types.CallbackQuery):
	current_timezone = db.get_timezone()

	await callback.message.edit_text(
		f"{E.CLOCK} <b>Настройка часового пояса</b>\n\n"
		f"📍 <b>Текущий пояс:</b> {current_timezone}\n\n"
		f"Выберите новый часовой пояс:",
		parse_mode="HTML",
		reply_markup=get_timezone_keyboard()
	)
	await callback.answer()

@router.callback_query(F.data.startswith("timezone_"))
async def set_timezone(callback: types.CallbackQuery):
	if callback.data == "timezone_back":
		# редактируем сообщение вместо отправки нового
		await callback.message.edit_text(
			get_settings_text(),
			parse_mode="HTML",
			reply_markup=get_settings_keyboard()
		)
		await callback.answer()
		return

	timezone = callback.data.replace("timezone_", "")

	# Проверяем валидность часового пояса
	try:
		pytz.timezone(timezone)
		success = db.set_timezone(timezone)

		if success:
			await callback.message.edit_text(
				f"{E.SUCCESS} Часовой пояс успешно изменен на:\n"
				f"<b>{timezone}</b>\n\n"
				f"Теперь все время будет указываться в этом часовом поясе.",
				parse_mode="HTML"
			)
		else:
			await callback.message.edit_text(
				f"{E.ERROR} Ошибка при сохранении часового пояса",
				parse_mode="HTML"
			)
	except pytz.UnknownTimeZoneError:
		await callback.message.edit_text(
			f"{E.ERROR} Неизвестный часовой пояс: {timezone}",
			parse_mode="HTML"
		)

	await callback.answer()

@router.callback_query(F.data == "settings_back")
async def settings_back(callback: types.CallbackQuery):
	await callback.message.edit_text(
		f"{E.HAND} Возврат в главное меню",
		reply_markup=get_admin_main_menu()
	)
	await callback.answer()