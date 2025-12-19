from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from utils.database import Database
from keyboards.keyboards import get_tests_list_keyboard, get_confirmation_keyboard
from states import TestDeletion
from utils.emoji import Emoji as E
from utils.callbacks import delete_test_cb

import logging

logger = logging.getLogger(__name__)
db = Database()
router = Router()


@router.message(lambda msg: bool(msg.text) and msg.text.strip() == f"{E.DELETE} Удалить тест")
async def start_test_deletion(message: types.Message, state: FSMContext):
    logger.info(f"[start_test_deletion] from={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        return

    tests = db.get_all_tests()
    if not tests:
        await message.answer(f"{E.POST_BOX} У вас пока нет созданных тестов для удаления")
        return

    await state.set_state(TestDeletion.waiting_for_test_selection)
    await message.answer("Выберите тест для удаления:", reply_markup=get_tests_list_keyboard(tests, action="delete"))


@router.callback_query(delete_test_cb.filter())
async def process_test_selection_for_deletion(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    """
    callback_data may be injected by aiogram when using real CallbackData.
    If not injected (fallback), parse it manually.
    """
    logger.info(f"[process_test_selection_for_deletion] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        # fallback parse
        callback_data = delete_test_cb.parse(callback.data or "")

    try:
        test_id = int(callback_data.get("test_id"))
    except Exception:
        await callback.answer()
        return

    if db.has_active_schedules(test_id):
        await callback.answer(f"{E.ERROR} Нельзя удалить тест с активными расписаниями!", show_alert=True)
        return

    await state.update_data(test_id=test_id)
    test = db.get_test(test_id)
    test_title = test[1] if test else "Неизвестный тест"
    await state.set_state(TestDeletion.waiting_for_confirmation)
    await callback.message.answer(
        f"{E.WARNING}️ Вы уверены, что хотите удалить тест:\n\n<b>{test_title}</b>\n\nЭто действие нельзя отменить!",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard(),
    )
    await callback.answer()


@router.callback_query(TestDeletion.waiting_for_confirmation, F.data == "confirm_delete")
async def confirm_test_deletion(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[confirm_test_deletion] user={callback.from_user.id}")
    data = await state.get_data()
    test_id = data.get("test_id")
    if test_id:
        test = db.get_test(test_id)
        if test:
            test_title = test[1]
            success = db.delete_test(test_id)
            if success:
                await callback.message.edit_text(f"{E.CONFIRM} Тест «{test_title}» успешно удален!")
            else:
                await callback.message.edit_text(f"{E.ERROR} Ошибка при удалении теста «{test_title}»")
    await state.clear()
    await callback.answer()


@router.callback_query(TestDeletion.waiting_for_confirmation, F.data == "cancel_delete")
async def cancel_test_deletion(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(f"{E.CANCEL} Удаление отменено")
    await callback.answer()