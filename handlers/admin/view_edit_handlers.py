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
from aiogram.types import FSInputFile, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

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
from utils.callbacks import ViewTestCB, StartEditCB, SessionEditCB, SessionDoneCB, \
    SessionCancelCB, DetailBackCB, get_callback_value, get_int_callback_value

from utils.config import load_config
from filters.admin_filters import IsAdminFilter

logger = logging.getLogger(__name__)
config = load_config()

router = Router()
router.message.filter(IsAdminFilter(config.admin_ids))
router.callback_query.filter(IsAdminFilter(config.admin_ids))


@router.callback_query(ViewTestCB.filter())
async def view_test_detail(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    logger.info(f"[view_test_detail] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = ViewTestCB.unpack(callback.data or "")

    # Получаем test_id через helper
    test_id = get_int_callback_value(callback_data, "test_id")
    if test_id is None:
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

    lines = [f"{E.TEXT} <b>{test[1]}</b> (ID: {test[0]})"]
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
            photo_msg = await callback.message.answer_photo(photo=FSInputFile(test[5]))
            await state.update_data(last_photo_message_id=photo_msg.message_id)
            await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))
        elif test[4]:
            photo_msg = await callback.message.answer_photo(photo=test[4])
            await state.update_data(last_photo_message_id=photo_msg.message_id)
            await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))
        else:
            await state.update_data(last_photo_message_id=None)
            await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))
    except Exception:
        logger.exception("Error while sending test detail")
        await state.update_data(last_photo_message_id=None)
        await callback.message.answer(details_text, parse_mode="HTML", reply_markup=get_test_detail_keyboard(test_id))

    await callback.answer()


@router.callback_query(DetailBackCB.filter())
async def detail_back(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    logger.info(f"[detail_back] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = DetailBackCB.unpack(callback.data or "")

    tests = db.get_all_tests()
    if not tests:
        await callback.message.answer("У вас нет тестов")
        await callback.answer()
        return

    # Delete the photo message if it exists
    data = await state.get_data()
    if last_photo_id := data.get('last_photo_message_id'):
        try:
            await callback.bot.delete_message(callback.message.chat.id, last_photo_id)
        except Exception:
            pass
        await state.update_data(last_photo_message_id=None)

    await callback.message.answer("Выберите тест для просмотра:", reply_markup=get_tests_view_keyboard(tests))
    await callback.answer()
    try:
        # attempt to delete the detailed message to avoid duplicates
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(StartEditCB.filter())
async def start_edit_session(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    logger.info(f"[start_edit_session] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        # Разбираем callback через .unpack()
        callback_data = StartEditCB.unpack(callback.data or "")

    test_id = get_int_callback_value(callback_data, "test_id")
    if test_id is None:
        await callback.answer()
        return

    await state.update_data(session_test_id=test_id)
    await state.set_state(EditSession.choosing_field)

    # remove reply keyboard and show inline session keyboard
    try:
        await callback.message.answer("​", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer("Режим редактирования. Выберите поле для правки:", reply_markup=get_edit_session_keyboard(test_id))
    await callback.answer()


@router.callback_query(SessionEditCB.filter())
async def session_choose_field(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    logger.info(f"[session_choose_field] user={callback.from_user.id} data={callback.data!r}")
    if callback_data is None:
        callback_data = SessionEditCB.unpack(callback.data or "")

    # Support dict or typed model
    if isinstance(callback_data, dict):
        test_id = callback_data.get("test_id")
        field = callback_data.get("field")
    elif hasattr(callback_data, "model_dump"):
        data = callback_data.model_dump()
        test_id = data.get("test_id")
        field = data.get("field")
    else:
        test_id = getattr(callback_data, "test_id", None)
        field = getattr(callback_data, "field", None)

    if not isinstance(test_id, int) or not isinstance(field, str):
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

    reply_markup = get_cancel_keyboard() if field != "photo" else InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{E.CANCEL} Отмена", callback_data=SessionCancelCB(test_id=test_id).pack())]
        ]
    )
    await callback.message.answer(prompts.get(field, "Введите значение:"), reply_markup=reply_markup)
    await callback.answer()


@router.message(EditSession.waiting_for_value, F.text)
async def session_receive_value(message: types.Message, state: FSMContext, db: Database):
    logger.info(f"[session_receive_value] user={message.from_user.id} text={message.text!r}")

    # Robust cancel detection: match "⚠️ Отмена" (E.CANCEL + 'Отмена') OR plain "Отмена" (case-insensitive)
    text = (message.text or "").strip()

    cancel_variants = {f"{E.CANCEL} Отмена".lower(), "отмена"}

    if text.lower() in cancel_variants:
        # If user cancels, clear the entire edit session and return to main menu
        await state.clear()
        try:
            await message.answer("​", reply_markup=ReplyKeyboardRemove())
        except Exception:
            pass
        await message.answer(f"{E.CANCEL} Режим редактирования отменён", reply_markup=get_tests_view_keyboard(db.get_all_tests()))
        logger.info(f"[session_receive_value] user={message.from_user.id} cancelled entire edit session")
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
                try:
                    await message.answer("​", reply_markup=ReplyKeyboardRemove())
                except Exception:
                    pass
            else:
                await message.answer(f"{E.ERROR} Не удалось обновить название")
        elif field == "text":
            val = message.text if message.text.strip() else None
            success = db.update_test(test_id, text_content=val)
            if success:
                await message.answer(f"{E.CONFIRM} Текст обновлён", reply_markup=get_edit_session_keyboard(test_id))
                try:
                    await message.answer("​", reply_markup=ReplyKeyboardRemove())
                except Exception:
                    pass
            else:
                await message.answer(f"{E.ERROR} Не удалось обновить текст")
        elif field == "question":
            success = db.update_test(test_id, question_text=message.text)
            if success:
                await message.answer(f"{E.CONFIRM} Вопрос обновлён", reply_markup=get_edit_session_keyboard(test_id))
                try:
                    await message.answer("​", reply_markup=ReplyKeyboardRemove())
                except Exception:
                    pass
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
                try:
                    await message.answer("​", reply_markup=ReplyKeyboardRemove())
                except Exception:
                    pass
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
            try:
                await message.answer("​", reply_markup=ReplyKeyboardRemove())
            except Exception:
                pass
            await message.answer(f"{E.CONFIRM} Картинка обновлена", reply_markup=get_edit_session_keyboard(test_id))
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
            try:
                await message.answer("​", reply_markup=ReplyKeyboardRemove())
            except Exception:
                pass
            await message.answer(f"{E.CONFIRM} Картинка обновлена", reply_markup=get_edit_session_keyboard(test_id))
        else:
            await message.answer(f"{E.ERROR} Не удалось обновить картинку")
    except Exception:
        logger.exception("Error while processing document image in session")
        await message.answer(f"{E.ERROR} Ошибка при обновлении картинки")

    await state.set_state(EditSession.choosing_field)


@router.callback_query(SessionDoneCB.filter())
async def session_done(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    logger.info(f"[session_done] user={callback.from_user.id}")
    if callback_data is None:
        # Разбираем callback через .unpack()
        callback_data = SessionDoneCB.unpack(callback.data or "")

    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.answer("​", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer(f"{E.CONFIRM} Редактирование завершено", reply_markup=get_tests_view_keyboard(db.get_all_tests()))
    await callback.answer()


@router.callback_query(SessionCancelCB.filter())
async def session_cancel(callback: types.CallbackQuery, state: FSMContext, db: Database, callback_data: dict | None = None):
    logger.info(f"[session_cancel] user={callback.from_user.id}")
    if callback_data is None:
        callback_data = SessionCancelCB.unpack(callback.data or "")

    await state.clear()
    try:
        await callback.message.answer("​", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer(f"{E.CANCEL} Режим редактирования отменён", reply_markup=get_tests_view_keyboard(db.get_all_tests()))
    await callback.answer()