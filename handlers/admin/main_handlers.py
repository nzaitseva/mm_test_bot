from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardRemove

import logging
import pytz
from datetime import datetime
import os
import json

from utils.database import Database
from keyboards.keyboards import get_admin_main_menu, get_tests_view_keyboard, get_settings_keyboard, get_tests_list_keyboard, get_schedules_list_keyboard
from utils.emoji import Emoji as E

logger = logging.getLogger(__name__)
db = Database()
router = Router()


@router.message(Command("admin"))
async def admin_start(message: types.Message, state: FSMContext):
    """Enter admin panel: clear FSM, check admin rights and show menu."""
    try:
        await state.clear()
    except Exception:
        logger.debug("Failed to clear FSM state on /admin (non-fatal)")

    logger.info(f"[admin_start] user={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        await message.answer(f"{E.CANCEL} У вас нет прав администратора")
        return

    try:
        await message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass

    await message.answer(
        f"{E.HAND} Добро пожаловать в панель администратора!\n"
        "Здесь вы можете создавать тесты и планировать их отправку в каналы.",
        reply_markup=get_admin_main_menu(),
    )


@router.message(lambda msg: bool(msg.text) and msg.text.strip() == f"{E.LIST} Мои тесты")
async def show_my_tests(message: types.Message):
    logger.info(f"[show_my_tests] from={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        return

    tests = db.get_all_tests()
    if not tests:
        await message.answer(f"{E.POST_BOX} У вас пока нет созданных тестов")
        return

    await message.answer("Выберите тест для просмотра:", reply_markup=get_tests_view_keyboard(tests))


@router.message(lambda msg: bool(msg.text) and ("Настройки" in msg.text or msg.text.strip() == f"{E.SETTINGS} Настройки"))
async def show_settings(message: types.Message):
    logger.info(f"[show_settings] from={message.from_user.id} text={message.text!r}")
    if not db.is_admin(message.from_user.id):
        return

    timezone = db.get_timezone()
    text = (
        f"{E.SETTINGS} <b>Настройки бота</b>\n\n"
        f"📍 <b>Текущий часовой пояс:</b> {timezone}\n\n"
        "Выберите настройку для изменения:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_settings_keyboard())


@router.message(lambda msg: bool(msg.text) and msg.text.strip() == f"{E.SCHEDULES} Активные расписания")
async def show_active_schedules(message: types.Message):
    logger.info(f"[show_active_schedules] from={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        return

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

    await message.answer(text + "Нажмите на расписание чтобы удалить его:", reply_markup=get_schedules_list_keyboard(schedules))