import logging
import os
import json
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardRemove

from utils.database import Database
from keyboards.keyboards import get_test_detail_keyboard, get_edit_session_keyboard, get_tests_view_keyboard, get_cancel_keyboard
from states import EditSession
from utils.emoji import Emoji as E
from utils.photo_manager import save_photo_from_message
from utils.callbacks import (
    view_test_cb,
    start_edit_cb,
    session_edit_cb,
    session_done_cb,
    session_cancel_cb,
)

logger = logging.getLogger(__name__)
db = Database()
router = Router()


@router.callback_query(view_test_cb.filter())
async def view_test_detail(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    logger.info(f"[view_test_detail] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = view_test_cb.parse(callback.data or "")
    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    try:
        test_id = int(callback_data.get("test_id"))
    except Exception:
        await callback.answer()
        return

    test = db.get_test(test_id)
    if not test:
        await callback.answer(f"{E.ERROR} Тест не найден", show_alert=True)
        return

    try:
        options = json.loads(test[7]) if test[7] else {}
    except Exception:
        options = {}

    lines = [f"📝 <b>{test[1]}</b> (ID: {test[0]})"]
    if test[3]:
        lines.append(f"\nТекст:\n{test[3]}")
    if test[6]:
        lines.append(f"\nВопрос:\n{test[6]}")
    lines.append("\nВарианты:")
    for opt, res in options.items():
        res_preview = res if len(res) <= 300 else res[:300] + "..."
        lines.append(f"• {opt} → {res_preview}")

    details_text = "\n".join(lines)

    try:
        if test[5] and os.path.exists(test[5]):
            await callback.message.answer_photo(photo=FSInputFile(test[5]))
            await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))
        elif test[4]:
            await callback.message.answer_photo(photo=test[4])
            await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))
        else:
            await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))
    except Exception:
        logger.exception("Error while sending test detail")
        await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))

    await callback.answer()


@router.callback_query(start_edit_cb.filter())
async def start_edit_session(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    logger.info(f"[start_edit_session] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = start_edit_cb.parse(callback.data or "")

    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    try:
        test_id = int(callback_data.get("test_id"))
    except Exception:
        await callback.answer()
        return

    await state.update_data(session_test_id=test_id)
    await state.set_state(EditSession.choosing_field)

    # remove reply keyboard and show inline session keyboard
    try:
        await callback.message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer("Режим редактирования. Выберите поле для правки:", reply_markup=get_edit_session_keyboard(test_id))
    await callback.answer()


@router.callback_query(session_edit_cb.filter())
async def session_choose_field(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    logger.info(f"[session_choose_field] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = session_edit_cb.parse(callback.data or "")

    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    try:
        test_id = int(callback_data.get("test_id"))
        field = callback_data.get("field")
    except Exception:
        await callback.answer()
        return

    if field not in ("title", "text", "photo", "question", "options"):
        await callback.answer()
        return

    await state.update_data(session_test_id=test_id, session_field=field)
    await state.set_state(EditSession.waiting_for_value)

    prompts = {
        "title": "Введите новое название:",
        "text": "Введите новый текст (или оставьте пустым чтобы очистить):",
        "photo": "Отправьте новое изображение (как фото или как файл):",
        "question": "Введите новый вопрос:",
        "options": "Введите варианты заново в формате:\nВариант :: Результат (каждый вариант с новой строки):",
    }

    await callback.message.answer(prompts.get(field, "Введите значение:"), reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.callback_query(session_done_cb.filter())
async def session_done(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    logger.info(f"[session_done] user={callback.from_user.id}")
    if callback_data is None:
        callback_data = session_done_cb.parse(callback.data or "")

    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer(f"{E.CONFIRM} Редактирование завершено", reply_markup=get_tests_view_keyboard(db.get_all_tests()))
    await callback.answer()


@router.callback_query(session_cancel_cb.filter())
async def session_cancel(callback: types.CallbackQuery, state: FSMContext, callback_data: dict | None = None):
    logger.info(f"[session_cancel] user={callback.from_user.id}")
    if callback_data is None:
        callback_data = session_cancel_cb.parse(callback.data or "")

    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer(f"{E.CANCEL} Режим редактирования отменён", reply_markup=get_tests_view_keyboard(db.get_all_tests()))
    await callback.answer()