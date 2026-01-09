"""
Entrance to admin panel (via /admin command):
    - `admin_start`

And main buttons (UX):
    - `show_my_tests` (a list of all added tests)
    - `show_settings` (bot settings)
    - `show_active_schedules` (tests planned to be sent to a channel)
"""

import logging
import pytz
from datetime import datetime

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from utils.emoji import Emoji as E
from utils.database import Database
from utils.config import load_config
from utils.callbacks import DeleteScheduleCB, ConfirmDeleteScheduleCB, CancelDeleteScheduleCB, \
    get_callback_value,get_int_callback_value
from filters.admin_filters import IsAdminFilter
from keyboards.keyboards import get_admin_main_menu, get_tests_view_keyboard, get_settings_keyboard, \
    get_schedules_list_keyboard, get_confirmation_keyboard


logger = logging.getLogger(__name__)
config = load_config()


router = Router()
# ALL handlers in this file are available only to admins
router.message.filter(IsAdminFilter(config.admin_ids))
router.callback_query.filter(IsAdminFilter(config.admin_ids))

@router.message(Command("admin"))
async def admin_start(message: types.Message, state: FSMContext):
    """Enter admin panel: clear FSM, check admin rights and show menu."""
    try:
        await state.clear()
    except Exception:
        logger.debug("Failed to clear FSM state on /admin (non-fatal)")

    logger.info(f"[admin_start] user={message.from_user.id}")

    await message.answer(
        f"{E.HAND} Добро пожаловать в панель администратора!\n"
        "Здесь вы можете создавать тесты и планировать их отправку в каналы.",
        reply_markup=get_admin_main_menu(),
    )


@router.message(F.text == f"{E.LIST} Мои тесты")
async def show_my_tests(message: types.Message, db: Database):
    logger.info(f"[show_my_tests] from={message.from_user.id}")

    tests = db.get_all_tests()
    if not tests:
        await message.answer(f"{E.POST_BOX} У вас пока нет созданных тестов")
        return

    await message.answer("Выберите тест для просмотра:", reply_markup=get_tests_view_keyboard(tests))


@router.message(F.text == f"{E.SETTINGS} Настройки")
async def show_settings(message: types.Message, db: Database):
    logger.info(f"[show_settings] from={message.from_user.id} text={message.text!r}")

    timezone = db.get_timezone()
    text = (
        f"{E.SETTINGS} <b>Настройки бота</b>\n\n"
        f"{E.STAPLE} <b>Текущий часовой пояс:</b> {timezone}\n\n"
        "Выберите настройку для изменения:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard())


@router.message(F.text == f"{E.SCHEDULES} Активные расписания")
async def show_active_schedules(message: types.Message, db: Database):
    logger.info(f"[show_active_schedules] from={message.from_user.id}")

    schedules = db.get_active_schedules()
    if not schedules:
        await message.answer(f"{E.POST_BOX} Нет активных расписаний")
        return

    timezone_str = db.get_timezone()
    tz = pytz.timezone(timezone_str)

    text = f"{E.SCHEDULES} Активные расписания ({timezone_str}):\n\n"
    for schedule_id, test_title, channel_id, scheduled_time in schedules:
        try:
            utc_time = datetime.fromisoformat(scheduled_time).replace(tzinfo=pytz.utc)
            local_time = utc_time.astimezone(tz)
            formatted_time = local_time.strftime("%d.%m.%Y %H:%M")
        except Exception:
            formatted_time = scheduled_time

        text += f"{E.STAPLE} {test_title}\n  {E.CALENDAR} {formatted_time}\n  {E.CHANNEL} {channel_id}\n\n"

    await message.answer(
        text + "Нажмите на расписание чтобы удалить его:",
        reply_markup=get_schedules_list_keyboard(schedules)
    )


@router.callback_query(DeleteScheduleCB.filter())
async def request_delete_schedule(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    logger.info(f"[request_delete_schedule] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = DeleteScheduleCB.unpack(callback.data or "")

    schedule_id = get_int_callback_value(callback_data, "schedule_id")
    if schedule_id is None:
        await callback.answer()
        return

    # Edit current message to request confirmation
    test_title = None
    try:
        rows = db._exec('SELECT t.title FROM schedule s JOIN tests t ON s.test_id = t.id WHERE s.id = ?', (int(schedule_id),), fetchone=True)
        test_title = rows[0] if rows else None
    except Exception:
        test_title = None

    text = f"{E.WARNING} Вы уверены, что хотите удалить расписание"
    if test_title:
        text += f" для теста: <b>{test_title}</b>"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_confirmation_keyboard(action="delete_schedule", item_id=schedule_id))
    await callback.answer()


@router.callback_query(ConfirmDeleteScheduleCB.filter())
async def confirm_delete_schedule(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    logger.info(f"[confirm_delete_schedule] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = ConfirmDeleteScheduleCB.unpack(callback.data or "")

    schedule_id = get_int_callback_value(callback_data, "schedule_id")
    if schedule_id is None:
        await callback.answer()
        return

    success = db.delete_schedule(schedule_id)
    if success:
        await callback.message.edit_text(f"{E.CONFIRM} Расписание удалено.")
    else:
        await callback.message.edit_text(f"{E.ERROR} Ошибка при удалении расписания.")
    await callback.answer()


@router.callback_query(CancelDeleteScheduleCB.filter())
async def cancel_delete_schedule(callback: types.CallbackQuery, callback_data: dict | None = None):
    if callback_data is None:
        callback_data = CancelDeleteScheduleCB.unpack(callback.data or "")

    await callback.message.edit_text(f"{E.CANCEL} Удаление отменено")
    await callback.answer()