from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
from utils.emoji import Emoji as E

def get_admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"{E.CREATE} Создать тест"), KeyboardButton(text=f"{E.SCHEDULE} Запланировать отправку")],
            [KeyboardButton(text=f"{E.LIST} Мои тесты"), KeyboardButton(text=f"{E.DELETE} Удалить тест")],
            [KeyboardButton(text=f"{E.SCHEDULES} Активные расписания"), KeyboardButton(text=f"{E.SETTINGS} Настройки")]
        ],
        resize_keyboard=True
    )

def get_settings_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{E.CLOCK} Часовой пояс", callback_data="settings_timezone")],
		]
    )

def get_timezone_keyboard():
	timezones = [
		("Москва (+3)", "Europe/Moscow"),
		("Екатеринбург (+5)", "Asia/Yekaterinburg"),
		("UTC (+0)", "UTC"),
	]

	buttons = []
	row = []
	for display_name, tz_name in timezones:
		row.append(InlineKeyboardButton(text=display_name, callback_data=f"timezone_{tz_name}"))
		if len(row) == 2:
			buttons.append(row)
			row = []
	if row:
		buttons.append(row)

	buttons.append([InlineKeyboardButton(text=f"{E.BACK} Назад", callback_data="timezone_back")])

	return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_content_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{E.TEXT} Только текст", callback_data="content_text")],
            [InlineKeyboardButton(text=f"{E.PHOTO} Только картинка", callback_data="content_photo")],
            [InlineKeyboardButton(text=f"{E.BOTH} Текст и картинка", callback_data="content_both")]
        ]
    )

def get_tests_list_keyboard(tests, action="select"):
	buttons = []
	for test_id, title in tests:
		if action == "delete":
			buttons.append([InlineKeyboardButton(text=f"{E.DELETE} {title}", callback_data=f"delete_test_{test_id}")])
		else:
			buttons.append([InlineKeyboardButton(text=f"{E.LIST} {title}", callback_data=f"select_test_{test_id}")])

	return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_schedules_list_keyboard(schedules):
	buttons = []
	for schedule_id, test_title, channel_id, scheduled_time in schedules:
		from datetime import datetime
		try:
			time_obj = datetime.fromisoformat(scheduled_time)
			formatted_time = time_obj.strftime("%d.%m.%Y %H:%M")
		except:
			formatted_time = scheduled_time

		button_text = f"{test_title} - {formatted_time}"
		if len(button_text) > 40:
			button_text = button_text[:37] + "..."

		buttons.append(
			[InlineKeyboardButton(text=f"{E.DELETE} {button_text}", callback_data=f"delete_schedule_{schedule_id}")])

	return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_options_keyboard(options):
	buttons = []
	for option_text in options.keys():
		button_text = option_text[:30] + "..." if len(option_text) > 30 else option_text
		buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"answer_{option_text}")])

	return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"{E.CANCEL} Отмена")]],
        resize_keyboard=True
    )

def get_confirmation_keyboard(action="delete"):
    if action == "delete_schedule":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{E.CONFIRM} Да, удалить расписание", callback_data="confirm_delete_schedule")],
                [InlineKeyboardButton(text=f"{E.CANCEL} Нет, отмена", callback_data="cancel_delete")]
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{E.CONFIRM} Да, удалить", callback_data="confirm_delete")],
                [InlineKeyboardButton(text=f"{E.CANCEL} Нет, отмена", callback_data="cancel_delete")]
            ]
        )