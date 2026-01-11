import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from utils.emoji import Emoji as E
from utils.database import Database
from utils.config import load_config
from keyboards.keyboards import get_cancel_keyboard, get_content_type_keyboard, get_admin_main_menu
from states import TestCreation
from filters.admin_filters import IsAdminFilter

config = load_config()
logger = logging.getLogger(__name__)


router = Router()
router.message.filter(IsAdminFilter(config.admin_ids))
router.callback_query.filter(IsAdminFilter(config.admin_ids))

@router.message(F.text == f"{E.CREATE} Создать тест")
async def start_test_creation(message: types.Message, state: FSMContext):
    logger.info(f"[start_test_creation] from={message.from_user.id}")

    await state.set_state(TestCreation.waiting_for_title)
    await message.answer("Введите название теста:", reply_markup=get_cancel_keyboard())


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
        await callback.message.answer(
            "Введите текстовое описание теста:",
            reply_markup=get_cancel_keyboard()
        )
    else:
        await state.set_state(TestCreation.waiting_for_photo)
        await callback.message.answer(
            "Отправьте картинку для теста:",
            reply_markup=get_cancel_keyboard())

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
        await message.answer("Отправьте картинку:", reply_markup=get_cancel_keyboard())


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
            await message.answer(
                f"{E.ERROR} Пожалуйста, отправьте изображение (как фото или файл).",
                reply_markup=get_cancel_keyboard()
            )
            return

        try:
            # use photo manager directly; db wrapper not required
            from utils.photo_manager import save_photo_from_message
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
async def process_options(message: types.Message, state: FSMContext, db: Database):
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