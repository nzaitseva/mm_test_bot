from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton,ReplyKeyboardMarkup, KeyboardButton

from utils.emoji import Emoji as E
from utils.callbacks import (
    SelectTestCB,
    DeleteTestCB,
    ViewTestCB,
    StartEditCB,
    SessionEditCB,
    SessionDoneCB,
    SessionCancelCB,
    TestOptionCB,
    DetailBackCB,
    TimezoneCB,
    DeleteScheduleCB,
    ConfirmDeleteScheduleCB,
    CancelDeleteScheduleCB,
    ConfirmDeleteTestCB,
    CancelDeleteTestCB,
    SettingsCB,
)


def get_admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"{E.CREATE} Создать тест"),
             KeyboardButton(text=f"{E.SCHEDULE} Запланировать отправку")],
            [KeyboardButton(text=f"{E.LIST} Мои тесты"), KeyboardButton(text=f"{E.DELETE} Удалить тест")],
            [KeyboardButton(text=f"{E.SCHEDULES} Активные расписания"), KeyboardButton(text=f"{E.SETTINGS} Настройки")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

"""
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"{E.CANCEL} Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
"""

def get_settings_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{E.CLOCK} Часовой пояс", callback_data=TimezoneCB(tz="open").pack())],
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
        row.append(InlineKeyboardButton(text=display_name, callback_data=TimezoneCB(tz=tz_name).pack()))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text=f"{E.BACK} Назад", callback_data=TimezoneCB(tz="back").pack())])

    buttons.append([InlineKeyboardButton(text=f"{E.CANCEL} Отмена", callback_data=SettingsCB(action="back").pack())])

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
            cb = DeleteTestCB(test_id=test_id).pack()
            buttons.append([InlineKeyboardButton(text=f"{E.DELETE} {title}", callback_data=cb)])
        else:
            cb = SelectTestCB(test_id=test_id).pack()
            buttons.append([InlineKeyboardButton(text=f"{E.LIST} {title}", callback_data=cb)])
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
            [InlineKeyboardButton(text=f"{E.DELETE} {button_text}", callback_data=DeleteScheduleCB(schedule_id=schedule_id).pack())])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_test_options_keyboard(options, test_id):
    buttons = []
    for option_text in options.keys():
        button_text = option_text[:30] + "..." if len(option_text) > 30 else option_text
        cb = TestOptionCB(test_id=test_id, option=option_text).pack()
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=f"{E.CANCEL} Отмена")]],
        resize_keyboard=True
    )


def get_confirmation_keyboard(action="delete", item_id: int | None = None):
    """Return a confirmation keyboard for the given action (supports typed callback data).

    If `item_id` is provided, typed callbacks will include the ID in callback_data;
    otherwise some fallback simple callbacks can be used (legacy).
    """
    if action == "delete_schedule":
        if item_id is None:
            raise ValueError("item_id required for delete_schedule confirmation")
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{E.CONFIRM} Да, удалить расписание",
                                      callback_data=ConfirmDeleteScheduleCB(schedule_id=item_id).pack())],
                [InlineKeyboardButton(text=f"{E.CANCEL} Нет, отмена", callback_data=CancelDeleteScheduleCB(schedule_id=item_id).pack())]
            ]
        )
    elif action == "delete_test":
        if item_id is None:
            raise ValueError("item_id required for delete_test confirmation")
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"{E.CONFIRM} Да, удалить",
                                      callback_data=ConfirmDeleteTestCB(test_id=item_id).pack())],
                [InlineKeyboardButton(text=f"{E.CANCEL} Нет, отмена", callback_data=CancelDeleteTestCB(test_id=item_id).pack())]
            ]
        )
    else:
        raise ValueError(f"Unsupported action for confirmation keyboard: {action}")


def get_tests_view_keyboard(tests):
    buttons = []
    for test_id, title in tests:
        cb = ViewTestCB(test_id=test_id).pack()
        buttons.append([InlineKeyboardButton(text=f"{E.SEARCH} {title}", callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_test_detail_keyboard(test_id):
    buttons = [
        [InlineKeyboardButton(text=f"{E.EDIT}️ Редактировать", callback_data=StartEditCB(test_id=test_id).pack())],
        [InlineKeyboardButton(text=f"{E.BACK} Назад", callback_data=DetailBackCB(test_id=test_id).pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_edit_session_keyboard(test_id):
    buttons = [
        [InlineKeyboardButton(text=f"{E.EDIT}️ Название", callback_data=SessionEditCB(test_id=test_id, field="title").pack()),
         InlineKeyboardButton(text=f"{E.EDIT}️ Текст", callback_data=SessionEditCB(test_id=test_id, field="text").pack())],
        [InlineKeyboardButton(text=f"{E.PHOTO} Картинка", callback_data=SessionEditCB(test_id=test_id, field="photo").pack()),
         InlineKeyboardButton(text=f"{E.QUESTION} Вопрос", callback_data=SessionEditCB(test_id=test_id, field="question").pack())],
        [InlineKeyboardButton(text=f"{E.TEXT} Варианты", callback_data=SessionEditCB(test_id=test_id, field="options").pack())],
        [InlineKeyboardButton(text=f"{E.CONFIRM} Готово", callback_data=SessionDoneCB(test_id=test_id).pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)