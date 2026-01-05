"""
View and edit added tests.

Functions for viewing tests:
    - `view_test_detail`
    - `detail_back`
    - `detail_back_legacy` - legacy/string handler, supports callback.data as "detail_back_{id}" (compatbility)

Functions for editing tests:
    - `start_edit_session` (CallbackData-based)
    - `session_choose_field` (CallbackData-based)
    - `session_receive_value` - Text handler: waiting for value,
                                supports cancelling the FIELD edit (returns to edit session)
                                and supports actual value updates.
    - `session_receive_photo` - Photo handler in edit session (compressed)
    - `session_receive_document_image` - Document image handler in edit session (uncompressed)
    - `session_done` - Done / Cancel callbacks for whole session
    - `session_cancel`
"""
import os
import json
import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, ReplyKeyboardRemove

from keyboards.keyboards import (
    get_test_detail_keyboard,
    get_edit_session_keyboard,
    get_tests_view_keyboard,
    get_cancel_keyboard,
)
from states import EditSession
from utils.database import Database
from utils.emoji import Emoji as E
from utils.photo_manager import save_photo_from_message
from utils.callbacks import (
    view_test_cb,
    start_edit_cb,
    session_edit_cb,
    session_done_cb,
    session_cancel_cb,
    detail_back_cb,
)
from utils.config import load_config
from filters.admin_filters import IsAdminFilter

logger = logging.getLogger(__name__)
config = load_config()

router = Router()
router.message.filter(IsAdminFilter(config.admin_ids))
router.callback_query.filter(IsAdminFilter(config.admin_ids))


@router.callback_query(view_test_cb.filter())
async def view_test_detail(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    """
    Show full details for a test. Uses callback factory view_test_cb.
    """
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
        # Prefer sending local file if exists, otherwise file_id or text only
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
        # fallback to plain text
        await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))

    await callback.answer()


@router.callback_query(detail_back_cb.filter())
async def detail_back(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    """
    Handler for the "Back" button created via detail_back_cb factory.
    Shows the tests list and attempts to delete the previous message (if possible).
    Compatible with real aiogram CallbackData injection and with fallback.
    """
    logger.info(f"[detail_back] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = detail_back_cb.parse(callback.data or "")

    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    tests = db.get_all_tests()
    if not tests:
        await callback.message.answer("У вас нет тестов")
        await callback.answer()
        return

    await callback.message.answer("Выберите тест для просмотра:", reply_markup=get_tests_view_keyboard(tests))
    await callback.answer()
    try:
        # attempt to delete the detailed message to avoid duplicates
        await callback.message.delete()
    except Exception:
        # ignore deletion errors (e.g., insufficient rights)
        pass


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("detail_back_"))
async def detail_back_legacy(callback: types.CallbackQuery, state: FSMContext, db: Database):
    logger.info(f"[detail_back_legacy] user={callback.from_user.id} data={callback.data!r}")
    # parse id from legacy string
    try:
        tid = callback.data.replace("detail_back_", "")
        test_id = int(tid)
    except Exception:
        await callback.answer()
        return

    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    tests = db.get_all_tests()
    if not tests:
        await callback.message.answer("У вас нет тестов")
        await callback.answer()
        return

    # Show tests list (same as modern handler)
    await callback.message.answer("Выберите тест для просмотра:", reply_markup=get_tests_view_keyboard(tests))
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(start_edit_cb.filter())
async def start_edit_session(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
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
async def session_choose_field(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
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


@router.message(EditSession.waiting_for_value, F.text)
async def session_receive_value(message: types.Message, state: FSMContext, db: Database):
    logger.info(f"[session_receive_value] user={message.from_user.id} text={message.text!r}")

    # Robust cancel detection: match "⚠️ Отмена" (E.CANCEL + 'Отмена') OR plain "Отмена" (case-insensitive)
    text = (message.text or "").strip()
    cancel_variants = {f"{E.CANCEL} Отмена".lower(), "отмена"}
    if text.lower() in cancel_variants:
        # If user cancels editing this field, return to choosing_field (do NOT clear whole session)
        data = await state.get_data()
        test_id = data.get("session_test_id")
        if test_id:
            await state.set_state(EditSession.choosing_field)
            # remove reply keyboard and show inline edit keyboard
            try:
                await message.answer(" ", reply_markup=ReplyKeyboardRemove())
            except Exception:
                pass
            await message.answer(f"{E.CANCEL} Изменение поля отменено. Выберите действие:", reply_markup=get_edit_session_keyboard(test_id))
            logger.info(f"[session_receive_value] user={message.from_user.id} cancelled edit of field, returned to choosing_field for test_id={test_id}")
            return
        else:
            # fallback: if session test id missing, clear state and go to main menu
            await state.clear()
            await message.answer("Изменение отменено", reply_markup=get_tests_view_keyboard(db.get_all_tests()))
            return

    # Otherwise — normal update flow
    data = await state.get_data()
    test_id = data.get("session_test_id")
    field = data.get("session_field")
    logger.debug(f"[session_receive_value] session_test_id={test_id} session_field={field}")
    if not test_id or not field:
        await message.answer(f"{E.ERROR} Внутренняя ошибка: test_id или поле не найдены")
        await state.clear()
        return

    try:
        if field == "title":
            success = db.update_test(test_id, title=message.text)
            if success:
                await message.answer(f"{E.CONFIRM} Название обновлено", reply_markup=get_edit_session_keyboard(test_id))
            else:
                await message.answer(f"{E.ERROR} Не удалось обновить название")
        elif field == "text":
            val = message.text if message.text.strip() else None
            success = db.update_test(test_id, text_content=val)
            if success:
                await message.answer(f"{E.CONFIRM} Текст обновлён", reply_markup=get_edit_session_keyboard(test_id))
            else:
                await message.answer(f"{E.ERROR} Не удалось обновить текст")
        elif field == "question":
            success = db.update_test(test_id, question_text=message.text)
            if success:
                await message.answer(f"{E.CONFIRM} Вопрос обновлён", reply_markup=get_edit_session_keyboard(test_id))
            else:
                await message.answer(f"{E.ERROR} Не удалось обновить вопрос")
        elif field == "options":
            options = {}
            for line in message.text.splitlines():
                if "::" in line:
                    opt, res = line.split("::", 1)
                    options[opt.strip()] = res.strip()
            if len(options) < 2:
                await message.answer(f"{E.ERROR} Нужно минимум 2 варианта. Попробуйте снова:")
                return
            success = db.update_test(test_id, options=options)
            if success:
                await message.answer(f"{E.CONFIRM} Варианты обновлены", reply_markup=get_edit_session_keyboard(test_id))
            else:
                await message.answer(f"{E.ERROR} Не удалось обновить варианты")
        elif field == "photo":
            await message.answer(f"{E.ERROR} Ожидается изображение. Пожалуйста, отправьте его как фото или файл (image/*).")
        else:
            await message.answer(f"{E.ERROR} Неподдерживаемое поле: {field}")
    except Exception:
        logger.exception("Error while updating field in session")
        await message.answer(f"{E.ERROR} Ошибка при обновлении")

    # return to choosing_field
    await state.set_state(EditSession.choosing_field)


@router.message(EditSession.waiting_for_value, F.photo)
async def session_receive_photo(message: types.Message, state: FSMContext, db: Database):
    logger.info(f"[session_receive_photo] user={message.from_user.id} photo=True")
    data = await state.get_data()
    test_id = data.get("session_test_id")
    field = data.get("session_field")
    if field != "photo":
        logger.debug("[session_receive_photo] Ignored: field != 'photo'")
        return

    try:
        photo_file_id = message.photo[-1].file_id
    except Exception:
        photo_file_id = None

    try:
        photo_path = ""
        try:
            photo_path = await save_photo_from_message(message)
        except Exception:
            logger.exception("Failed to save photo in edit session")
            photo_path = ""

        success = db.update_test(test_id, photo_file_id=photo_file_id, photo_path=photo_path)
        if success:
            await message.answer(f"{E.CONFIRM} Картинка обновлена", reply_markup=get_edit_session_keyboard(test_id))
            try:
                await message.answer(" ", reply_markup=ReplyKeyboardRemove())
            except Exception:
                pass
        else:
            await message.answer(f"{E.ERROR} Не удалось обновить картинку")
    except Exception:
        logger.exception("Error updating photo in session")
        await message.answer(f"{E.ERROR} Ошибка при обновлении картинки")

    await state.set_state(EditSession.choosing_field)


@router.message(EditSession.waiting_for_value, F.document)
async def session_receive_document_image(message: types.Message, state: FSMContext, db: Database):
    logger.info(f"[session_receive_document_image] user={message.from_user.id} document=True mime={getattr(message.document,'mime_type',None)}")
    if not getattr(message, "document", None):
        return
    if not getattr(message.document, "mime_type", "").startswith("image"):
        return

    data = await state.get_data()
    test_id = data.get("session_test_id")
    field = data.get("session_field")
    if field != "photo":
        logger.debug("[session_receive_document_image] Ignored: field != 'photo'")
        return

    try:
        file_id = message.document.file_id
        photo_path = ""
        try:
            photo_path = await save_photo_from_message(message)
        except Exception:
            logger.exception("Failed to save document image in edit session")
            photo_path = ""

        success = db.update_test(test_id, photo_file_id=file_id, photo_path=photo_path)
        if success:
            await message.answer(f"{E.CONFIRM} Картинка обновлена", reply_markup=get_edit_session_keyboard(test_id))
            try:
                await message.answer(" ", reply_markup=ReplyKeyboardRemove())
            except Exception:
                pass
        else:
            await message.answer(f"{E.ERROR} Не удалось обновить картинку")
    except Exception:
        logger.exception("Error while processing document image in session")
        await message.answer(f"{E.ERROR} Ошибка при обновлении картинки")

    await state.set_state(EditSession.choosing_field)


@router.callback_query(session_done_cb.filter())
async def session_done(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
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
async def session_cancel(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
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