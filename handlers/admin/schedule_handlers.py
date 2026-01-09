import pytz
import logging
from datetime import datetime

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from keyboards.keyboards import get_tests_list_keyboard, get_cancel_keyboard, get_admin_main_menu
from states import ScheduleCreation
from utils.database import Database
from utils.emoji import Emoji as E
from utils.callbacks import SelectTestCB, get_int_callback_value
from utils.config import load_config
from filters.admin_filters import IsAdminFilter

logger = logging.getLogger(__name__)
config = load_config()

router = Router()
router.message.filter(IsAdminFilter(config.admin_ids))
router.callback_query.filter(IsAdminFilter(config.admin_ids))

@router.message(F.text == f"{E.SCHEDULE} Запланировать отправку")
async def start_scheduling(message: types.Message, state: FSMContext, db: Database):
    logger.info(f"[start_scheduling] from={message.from_user.id}")

    tests = db.get_all_tests()
    if not tests:
        await message.answer(f"{E.ERROR} Сначала создайте тест")
        return

    await state.set_state(ScheduleCreation.waiting_for_test_selection)
    await message.answer("Выберите тест для отправки:", reply_markup=get_tests_list_keyboard(tests))


@router.message(F.text == f"{E.CANCEL} Отмена")
async def cancel_scheduling(message: types.Message, state: FSMContext):
    """Unified cancel handler for schedule creation states."""
    st = await state.get_state()
    # we explicitly check known scheduling states to avoid intercepting other flows
    if st in (
        ScheduleCreation.waiting_for_test_selection,
        ScheduleCreation.waiting_for_channel,
        ScheduleCreation.waiting_for_time,
    ):
        await state.clear()
        await message.answer(f"{E.CANCEL} Планирование отменено", reply_markup=get_admin_main_menu())
        return


@router.callback_query(SelectTestCB.filter())
async def process_test_selection(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    logger.info(f"[process_test_selection] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = SelectTestCB.unpack(callback.data or "")

    test_id = get_int_callback_value(callback_data, "test_id")
    if test_id is None:
        await callback.answer()
        return

    await state.update_data(test_id=test_id)
    await state.set_state(ScheduleCreation.waiting_for_channel)
    await callback.message.answer(
        "Введите ID или @username канала (например: @my_channel или -1001234567890):",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(ScheduleCreation.waiting_for_channel)
async def process_channel(message: types.Message, state: FSMContext):
    logger.info(f"[process_channel] from={message.from_user.id} text={message.text!r}")

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
async def process_time(message: types.Message, state: FSMContext, db: Database):
    logger.info(f"[process_time] from={message.from_user.id} text={message.text!r}")
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