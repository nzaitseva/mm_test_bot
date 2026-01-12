""""
Functions for deleting tests from admin panel.
"""
import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from keyboards.keyboards import get_tests_list_keyboard, get_confirmation_keyboard
from states import TestDeletion
from utils.database import Database
from utils.emoji import Emoji as E
from utils.callbacks import DeleteTestCB, ConfirmDeleteTestCB, CancelDeleteTestCB, get_int_callback_value
from utils.config import load_config
from filters.admin_filters import IsAdminFilter

config = load_config()

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(IsAdminFilter(config.admin_ids))
router.callback_query.filter(IsAdminFilter(config.admin_ids))

@router.message(F.text == f"{E.DELETE} Удалить тест")
async def start_test_deletion(message: types.Message, state: FSMContext, db: Database):
    logger.info(f"[start_test_deletion] from={message.from_user.id}")

    tests = db.get_all_tests()
    if not tests:
        await message.answer(f"{E.POST_BOX} У вас пока нет созданных тестов для удаления")
        return

    await state.set_state(TestDeletion.waiting_for_test_selection)
    await message.answer("Выберите тест для удаления:", reply_markup=get_tests_list_keyboard(tests, action="delete"))


@router.callback_query(DeleteTestCB.filter())
async def process_test_selection_for_deletion(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    logger.info(f"[process_test_selection_for_deletion] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = DeleteTestCB.unpack(callback.data or "")

    test_id = get_int_callback_value(callback_data, "test_id")
    if test_id is None:
        await callback.answer()
        return

    if db.has_active_schedules(test_id):
        await callback.answer(f"{E.ERROR} Нельзя удалить тест с активными расписаниями!", show_alert=True)
        return

    test = db.get_test(test_id)
    test_title = test[1] if test else "Неизвестный тест"
    await callback.message.answer(
        f"{E.WARNING}️ Вы уверены, что хотите удалить тест:\n\n<b>{test_title}</b>\n\nЭто действие нельзя отменить!",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard(action="delete_test", item_id=test_id),
    )
    await callback.answer()


@router.callback_query(ConfirmDeleteTestCB.filter())
async def confirm_test_deletion(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    logger.info(f"[confirm_test_deletion] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = ConfirmDeleteTestCB.unpack(callback.data or "")

    test_id = get_int_callback_value(callback_data, "test_id")
    if test_id is None:
        await callback.answer()
        return

    test = db.get_test(test_id)
    if test:
        test_title = test[1]
        success = db.delete_test(test_id)
        if success:
            await callback.message.edit_text(f"{E.CONFIRM} Тест «{test_title}» успешно удален!")
        else:
            await callback.message.edit_text(f"{E.ERROR} Ошибка при удалении теста «{test_title}»")

    await callback.answer()


@router.callback_query(CancelDeleteTestCB.filter())
async def cancel_test_deletion(callback: types.CallbackQuery, callback_data: dict | None = None):
    if callback_data is None:
        callback_data = CancelDeleteTestCB.unpack(callback.data or "")

    await callback.message.edit_text(f"{E.CANCEL} Удаление отменено")
    await callback.answer()