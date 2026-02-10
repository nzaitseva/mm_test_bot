""""
Sending tests to a channel and processing responses (test_option)
"""
import os
import json
import logging

from aiogram import Router, F, types
from aiogram.types import FSInputFile

from utils.database import Database
from utils.emoji import Emoji as E
from utils.callbacks import TestOptionCB, get_callback_value
from keyboards.keyboards import get_test_options_keyboard


logger = logging.getLogger(__name__)

router = Router()


async def send_test_to_channel(test_id, channel_id, bot, db: Database):
    test = await db.get_test(test_id)
    if not test:
        logger.error(f"{E.ERROR} Тест {test_id} не найден для отправки в канал {channel_id}")
        return False

    test_data = {
        'id': test[0],
        'title': test[1],
        'content_type': test[2],
        'text_content': test[3],
        'photo_file_id': test[4],
        'photo_path': test[5],
        'question_text': test[6],
        'options': json.loads(test[7])
    }

    keyboard = get_test_options_keyboard(test_data['options'], test_data['id'])

    try:
        if test_data['content_type'] == 'text':
            await bot.send_message(
                chat_id=channel_id,
                text=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['text_content']}\n\n{test_data['question_text']}",
                reply_markup=keyboard
            )
        elif test_data['content_type'] == 'photo':
            if test_data.get('photo_path') and os.path.exists(test_data['photo_path']):
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=FSInputFile(test_data['photo_path']),
                    caption=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['question_text']}",
                    reply_markup=keyboard
                )
            elif test_data.get('photo_file_id'):
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=test_data['photo_file_id'],
                    caption=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['question_text']}",
                    reply_markup=keyboard
                )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['question_text']}",
                    reply_markup=keyboard
                )
        elif test_data['content_type'] == 'both':
            if test_data.get('photo_path') and os.path.exists(test_data['photo_path']):
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=FSInputFile(test_data['photo_path']),
                    caption=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['text_content']}\n\n{test_data['question_text']}",
                    reply_markup=keyboard
                )
            elif test_data.get('photo_file_id'):
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=test_data['photo_file_id'],
                    caption=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['text_content']}\n\n{test_data['question_text']}",
                    reply_markup=keyboard
                )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=f"{E.PUZZLE} {test_data['title']}\n\n{test_data['text_content']}\n\n{test_data['question_text']}",
                    reply_markup=keyboard
                )
        return True
    except Exception as e:
        logger.error(f"{E.ERROR} Ошибка отправки теста {test_id} в {channel_id}: {e}")
        return False


@router.callback_query(TestOptionCB.filter())
async def handle_test_answer(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    if callback_data is None:
        callback_data = TestOptionCB.unpack(callback.data or "")

    try:
        test_id_raw = get_callback_value(callback_data, "test_id")
        option_text = get_callback_value(callback_data, "option")
        try:
            test_id = int(test_id_raw)
        except Exception:
            raise
        logger.info(f"📨 Получен callback_data: test_id={test_id}, option={option_text!r}")

        test = await db.get_test(test_id)
        if not test:
            logger.error(f"{E.ERROR} Тест {test_id} не найден")
            await callback.answer(f"{E.ERROR} Тест не найден", show_alert=True)
            return

        options = json.loads(test[7])
        logger.info(f"{E.SEARCH} Варианты в тесте {test_id}: {list(options.keys())}")

        if option_text in options:
            result_text = options[option_text]
            if result_text and result_text.strip():
                alert_text = result_text[:200]
                await callback.answer(alert_text, show_alert=True)
            else:
                await callback.answer(f"{E.INFO} Для этого варианта результат пока не настроен", show_alert=True)
        else:
            logger.warning(f"{E.WARNING} Вариант '{option_text}' не найден в тесте {test_id}")
            await callback.answer(f"{E.ERROR} Вариант ответа не найден", show_alert=True)

    except Exception as e:
        logger.exception(f"{E.ERROR} Ошибка в обработчике ответов: {e}")
        await callback.answer(f"{E.ERROR} Произошла ошибка", show_alert=True)