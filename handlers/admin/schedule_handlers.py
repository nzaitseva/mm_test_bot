import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from utils.database import Database
from keyboards.keyboards import get_tests_list_keyboard, get_cancel_keyboard, get_admin_main_menu
from states import ScheduleCreation
from utils.emoji import Emoji as E
from utils.callbacks import select_test_cb
import pytz
from datetime import datetime

logger = logging.getLogger(__name__)
db = Database()
router = Router()


@router.message(lambda msg: bool(msg.text) and msg.text.strip() == f"{E.SCHEDULE} Запланировать отправку")
async def start_scheduling(message: types.Message, state: FSMContext):
    logger.info(f"[start_scheduling] from={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        return

    tests = db.get_all_tests()
    if not tests:
        await message.answer(f"{E.ERROR} Сначала создайте тест")
        return

    await state.set_state(ScheduleCreation.waiting_for_test_selection)
    await message.answer("Выберите тест для отправки:", reply_markup=get_tests_list_keyboard(tests))


@router.callback_query(select_test_cb.filter())
async def process_test_selection(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    """
    callback_data may be injected by aiogram when using real CallbackData.
    If not injected (fallback), parse it manually.
    """
    logger.info(f"[process_test_selection] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        # fallback parse
        callback_data = select_test_cb.parse(callback.data or "")

    try:
        test_id = int(callback_data.get("test_id"))
    except Exception:
        await callback.answer()
        return

    await state.update_data(test_id=test_id)
    await state.set_state(ScheduleCreation.waiting_for_channel)
    await callback.message.answer("Введите ID или @username канала (например: @my_channel или -1001234567890):", reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(ScheduleCreation.waiting_for_channel)
async def process_channel(message: types.Message, state: FSMContext):
    logger.info(f"[process_channel] from={message.from_user.id} text={message.text!r}")
    if message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        await message.answer(f"{E.CANCEL} Планирование отменено", reply_markup=get_admin_main_menu())
        return

    channel_id = Database.parse_channel_input(message.text)
    await state.update_data(channel_id=channel_id)
    await state.set_state(ScheduleCreation.waiting_for_time)
    await message.answer(
        f"{E.CHANNEL} Канал распознан как: <code>{channel_id}</code>\n\n"
        f"{E.CLOCK} Введите время отправки в формате ДД.MM.ГГГГ ЧЧ:ММ\n"
        "Например: 25.12.2024 15:30",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(ScheduleCreation.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    logger.info(f"[process_time] from={message.from_user.id} text={message.text!r}")
    if message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        await message.answer(f"{E.CANCEL} Планирование отменено", reply_markup=get_admin_main_menu())
        return
    try:
        timezone_str = db.get_timezone()
        tz = pytz.timezone(timezone_str)
        local_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        localized_time = tz.localize(local_time)
        utc_time = localized_time.astimezone(pytz.utc)

        data = await state.get_data()
        db.add_schedule(data["test_id"], data["channel_id"], utc_time)

        test = db.get_test(data["test_id"])
        test_title = test[1] if test else "Неизвестный тест"
        await message.answer(
            f"{E.CONFIRM} Тест '{test_title}' запланирован!\n"
            f"{E.CALENDAR} Дата: {local_time.strftime('%d.%m.%Y %H:%M')} ({timezone_str})\n"
            f"{E.CHANNEL} Канал: {data['channel_id']}",
            reply_markup=get_admin_main_menu(),
        )
        await state.clear()
    except ValueError:
        await message.answer(f"{E.ERROR} Неверный формат времени. Используйте: ДД.MM.ГГГГ ЧЧ:ММ\nПример: 25.12.2024 15:30")