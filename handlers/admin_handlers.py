import logging
import os
import json
from datetime import datetime

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardRemove

from utils.database import Database
from keyboards.keyboards import *
from states import (
    TestCreation,
    ScheduleCreation,
    TestDeletion,
    ScheduleDeletion,
    EditTest,
    EditSession,
)
from utils.emoji import Emoji as E
from utils.channel_utils import parse_channel_input
from utils.photo_manager import save_photo_from_message
import pytz

logger = logging.getLogger(__name__)

router = Router()
db = Database()


# -----------------------
# ADMIN ENTRY
# -----------------------
@router.message(Command("admin"))
async def admin_start(message: types.Message, state: FSMContext):
    """Enter admin panel: clear FSM, check admin rights and show menu."""
    try:
        await state.clear()
    except Exception:
        logger.exception("Failed to clear state on /admin")

    logger.info(f"[admin_start] user={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        logger.info(f"[admin_start] user is not admin: {message.from_user.id}")
        await message.answer(f"{E.CANCEL} У вас нет прав администратора")
        return

    # remove any reply keyboard left
    try:
        await message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass

    await message.answer(
        f"{E.HAND} Добро пожаловать в панель администратора!\n"
        "Здесь вы можете создавать тесты и планировать их отправку в каналы.",
        reply_markup=get_admin_main_menu(),
    )


# -----------------------
# MAIN MENU BUTTONS (robust: use strip comparison)
# -----------------------
@router.message(lambda msg: bool(msg.text) and msg.text.strip() == f"{E.LIST} Мои тесты")
async def show_my_tests(message: types.Message):
    logger.info(f"[show_my_tests] from={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        logger.info(f"[show_my_tests] Non-admin access attempt: {message.from_user.id}")
        return

    tests = db.get_all_tests()
    if not tests:
        await message.answer(f"{E.POST_BOX} У вас пока нет созданных тестов")
        return

    await message.answer("Выберите тест для просмотра:", reply_markup=get_tests_view_keyboard(tests))


@router.message(lambda msg: bool(msg.text) and msg.text.strip() == f"{E.CREATE} Создать тест")
async def start_test_creation(message: types.Message, state: FSMContext):
    logger.info(f"[start_test_creation] from={message.from_user.id}")
    if not db.is_admin(message.from_user.id):
        return

    await state.set_state(TestCreation.waiting_for_title)
    await message.answer("Введите название теста:", reply_markup=get_cancel_keyboard())


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


# -----------------------
# SETTINGS BUTTON (robust)
# -----------------------
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


# -----------------------
# TEST CREATION FSM
# -----------------------
@router.message(TestCreation.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    logger.info(f"[process_title] from={message.from_user.id} text={message.text!r}")
    if message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
        return

    await state.update_data(title=message.text)
    await state.set_state(TestCreation.waiting_for_content_type)
    await message.answer("Выберите тип контента:", reply_markup=get_content_type_keyboard())


@router.callback_query(TestCreation.waiting_for_content_type, F.data.startswith("content_"))
async def process_content_type(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[process_content_type] user={callback.from_user.id} data={callback.data!r}")
    content_type = callback.data.replace("content_", "")
    await state.update_data(content_type=content_type)

    if content_type in ("text", "both"):
        await state.set_state(TestCreation.waiting_for_text_content)
        await callback.message.answer("Введите текстовое содержание теста:", reply_markup=get_cancel_keyboard())
    else:
        await state.set_state(TestCreation.waiting_for_photo)
        await callback.message.answer("Отправьте картинку для теста:", reply_markup=get_cancel_keyboard())

    await callback.answer()


@router.message(TestCreation.waiting_for_text_content)
async def process_text_content(message: types.Message, state: FSMContext):
    logger.info(f"[process_text_content] from={message.from_user.id}")
    if message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
        return

    await state.update_data(text_content=message.text)
    data = await state.get_data()
    if data.get("content_type") == "text":
        await state.set_state(TestCreation.waiting_for_question)
        await message.answer("Введите вопрос теста:", reply_markup=get_cancel_keyboard())
    else:
        await state.set_state(TestCreation.waiting_for_photo)
        await message.answer("Теперь отправьте картинку:", reply_markup=get_cancel_keyboard())


@router.message(TestCreation.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    logger.info(f"[process_photo_create] from={message.from_user.id} photo={bool(getattr(message,'photo',None))} document={bool(getattr(message,'document',None))}")
    if getattr(message, "text", None) and message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
        return

    photo_file_id = None
    try:
        if getattr(message, "photo", None):
            photo_file_id = message.photo[-1].file_id
        elif getattr(message, "document", None) and getattr(message.document, "mime_type", "").startswith("image"):
            photo_file_id = message.document.file_id
        else:
            await message.answer(f"{E.ERROR} Пожалуйста, отправьте изображение (как фото или файл).", reply_markup=get_cancel_keyboard())
            return

        try:
            photo_path = await save_photo_from_message(message)
        except Exception:
            logger.exception("Failed to save photo in creation")
            photo_path = ""

        await state.update_data(photo_file_id=photo_file_id, photo_path=photo_path)
        data = await state.get_data()
        if data.get("content_type") == "photo" or "text_content" in data:
            await state.set_state(TestCreation.waiting_for_question)
            await message.answer("Введите вопрос теста:", reply_markup=get_cancel_keyboard())

    except Exception:
        logger.exception("Error while processing photo for creation")
        await message.answer(f"{E.ERROR} Произошла ошибка при обработке изображения")


@router.message(TestCreation.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    logger.info(f"[process_question] from={message.from_user.id}")
    if message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
        return

    await state.update_data(question=message.text)
    await state.set_state(TestCreation.waiting_for_options)
    await message.answer(
        f"{E.TEXT} Введите варианты ответов в формате:\n"
        "Вариант1 :: Результат1 (до 200 символов)\n"
        "Вариант2 :: Результат2 (до 200 символов)\n\n"
        f"{E.LAMP} Пример:\n"
        "Волны :: Текст результата\n"
        "Дерево :: Другой результат",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(TestCreation.waiting_for_options)
async def process_options(message: types.Message, state: FSMContext):
    logger.info(f"[process_options] from={message.from_user.id}")
    if message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        await message.answer(f"{E.CANCEL} Создание теста отменено", reply_markup=get_admin_main_menu())
        return

    try:
        options = {}
        for line in message.text.splitlines():
            if "::" in line:
                opt, res = line.split("::", 1)
                options[opt.strip()] = res.strip()
        if len(options) < 2:
            await message.answer(f"{E.ERROR} Нужно минимум 2 варианта. Попробуйте еще раз:")
            return

        data = await state.get_data()
        test_id = db.add_test(
            title=data.get("title"),
            content_type=data.get("content_type"),
            text_content=data.get("text_content", ""),
            photo_file_id=data.get("photo_file_id", ""),
            photo_path=data.get("photo_path", ""),
            question_text=data.get("question"),
            options=options,
        )

        await message.answer(f"{E.SUCCESS} Тест '{data.get('title')}' создан (ID: {test_id})", reply_markup=get_admin_main_menu())
        await state.clear()
    except Exception:
        logger.exception("Error while finishing test creation")
        await message.answer(f"{E.ERROR} Ошибка при сохранении теста")


# -----------------------
# SCHEDULING FSM
# -----------------------
@router.callback_query(ScheduleCreation.waiting_for_test_selection, F.data.startswith("select_test_"))
async def process_test_selection(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[process_test_selection] user={callback.from_user.id} data={callback.data!r}")
    test_id_part = callback.data.replace("select_test_", "")
    if not test_id_part.isdigit():
        await callback.answer()
        return
    test_id = int(test_id_part)

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

    channel_id = parse_channel_input(message.text)
    await state.update_data(channel_id=channel_id)
    await state.set_state(ScheduleCreation.waiting_for_time)
    await message.answer(
        f"{E.CHANNEL} Канал распознан как: <code>{channel_id}</code>\n\n"
        f"{E.CLOCK} Введите время отправки в формате ДД.MM.ГГГГ ЧЧ:ММ\n"
        "Например: 25.12.2024 15:30",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )


# -----------------------
# DELETION FSM
# -----------------------
@router.callback_query(TestDeletion.waiting_for_test_selection, F.data.startswith("delete_test_"))
async def process_test_selection_for_deletion(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[process_test_selection_for_deletion] user={callback.from_user.id} data={callback.data!r}")
    test_id_part = callback.data.replace("delete_test_", "")
    if not test_id_part.isdigit():
        await callback.answer()
        return
    test_id = int(test_id_part)

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


# -----------------------
# VIEW A TEST (callback)
# -----------------------
@router.callback_query(lambda c: bool(c.data) and c.data.startswith("view_test_"))
async def view_test_detail(callback: types.CallbackQuery):
    logger.info(f"[view_test_detail] user={callback.from_user.id} data={callback.data!r}")
    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    test_id_part = callback.data.replace("view_test_", "")
    if not test_id_part.isdigit():
        await callback.answer()
        return
    test_id = int(test_id_part)

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


# -----------------------
# EDIT SESSION (comfortable multi-field editing)
# -----------------------
@router.callback_query(lambda c: bool(c.data) and c.data.startswith("start_edit_session_"))
async def start_edit_session(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[start_edit_session] user={callback.from_user.id} data={callback.data!r}")
    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    payload = callback.data.replace("start_edit_session_", "")
    if not payload.isdigit():
        await callback.answer()
        return
    test_id = int(payload)

    await state.update_data(session_test_id=test_id)
    await state.set_state(EditSession.choosing_field)

    # remove reply keyboard and show inline session keyboard
    try:
        await callback.message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer("Режим редактирования. Выберите поле для правки:", reply_markup=get_edit_session_keyboard(test_id))
    await callback.answer()


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("session_edit_"))
async def session_choose_field(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[session_choose_field] user={callback.from_user.id} data={callback.data!r}")
    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return

    parts = callback.data.split("_", 3)
    if len(parts) != 4:
        await callback.answer()
        return

    test_id_str = parts[2]
    field = parts[3]
    if not test_id_str.isdigit():
        await callback.answer()
        return
    test_id = int(test_id_str)

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


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("session_done_"))
async def session_done(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[session_done] user={callback.from_user.id}")
    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer(f"{E.CONFIRM} Редактирование завершено", reply_markup=get_admin_main_menu())
    await callback.answer()


@router.callback_query(lambda c: bool(c.data) and c.data.startswith("session_cancel_"))
async def session_cancel(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[session_cancel] user={callback.from_user.id}")
    if not db.is_admin(callback.from_user.id):
        await callback.answer()
        return
    await state.clear()
    try:
        await callback.message.answer(" ", reply_markup=ReplyKeyboardRemove())
    except Exception:
        pass
    await callback.message.answer(f"{E.CANCEL} Режим редактирования отменён", reply_markup=get_admin_main_menu())
    await callback.answer()


@router.message(EditSession.waiting_for_value, F.text)
async def session_receive_value(message: types.Message, state: FSMContext):
    logger.info(f"[session_receive_value] user={message.from_user.id} text={message.text!r}")
    # cancel via reply keyboard
    if message.text == f"{E.CANCEL} Отмена":
        await state.clear()
        try:
            await message.answer(" ", reply_markup=ReplyKeyboardRemove())
        except Exception:
            pass
        await message.answer("Изменение отменено", reply_markup=get_admin_main_menu())
        return

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
async def session_receive_photo(message: types.Message, state: FSMContext):
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
async def session_receive_document_image(message: types.Message, state: FSMContext):
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


# -----------------------
# SETTINGS: Back button from details
# -----------------------
@router.callback_query(lambda c: bool(c.data) and c.data.startswith("detail_back_"))
async def detail_back(callback: types.CallbackQuery):
    logger.info(f"[detail_back] user={callback.from_user.id} data={callback.data!r}")
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
        await callback.message.delete()
    except Exception:
        pass

# End of admin_handlers (no catch-all handlers here)