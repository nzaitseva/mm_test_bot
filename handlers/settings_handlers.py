import pytz
import logging

from aiogram import Router, F, types

from utils.emoji import Emoji as E
from utils.database import Database
from utils.config import load_config
from utils.callbacks import TimezoneCB, SettingsCB, get_callback_value
from filters.admin_filters import IsAdminFilter
from keyboards.keyboards import get_settings_keyboard, get_timezone_keyboard, get_admin_main_menu


logger = logging.getLogger(__name__)
config = load_config()

router = Router()
router.message.filter(IsAdminFilter(config.admin_ids))
router.callback_query.filter(IsAdminFilter(config.admin_ids))


def get_settings_text(db: Database):
    current_timezone = db.get_timezone()
    return (
        f"{E.SETTINGS} <b>Настройки бота</b>\n\n"
        f"{E.STAPLE} <b>Текущий часовой пояс:</b> {current_timezone}\n\n"
        f"Выберите настройку для изменения:"
    )


@router.message(F.text == f"{E.SETTINGS} Настройки")
async def show_settings(message: types.Message, db: Database):
    await message.answer(get_settings_text(db), parse_mode="HTML", reply_markup=get_settings_keyboard())


@router.callback_query(TimezoneCB.filter(F.tz == "open"))
# Handles only opening of timezone lists (tz == "open").
async def show_timezone_settings(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    if callback_data is None:
        callback_data = TimezoneCB.unpack(callback.data or "")

    tz_val = get_callback_value(callback_data, "tz")
    if tz_val == "open":
        current_timezone = db.get_timezone()
        await callback.message.edit_text(
            f"{E.CLOCK} <b>Настройка часового пояса</b>\n\n"
            f"{E.STAPLE} <b>Текущий пояс:</b> {current_timezone}\n\n"
            f"Выберите новый часовой пояс:",
            parse_mode="HTML",
            reply_markup=get_timezone_keyboard()
        )
    else:
        # ignore other tz actions here (handled in set_timezone)
        pass
    await callback.answer()


@router.callback_query(TimezoneCB.filter(F.tz != "open"))
async def set_timezone(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    if callback_data is None:
        callback_data = TimezoneCB.unpack(callback.data or "")

    tz = get_callback_value(callback_data, "tz")

    if tz == "back":

        await callback.message.edit_text(
            get_settings_text(db),
            parse_mode="HTML", reply_markup=get_settings_keyboard()
        )
        await callback.answer()
        return

    try:
        pytz.timezone(tz)
        success = db.set_timezone(tz)
        if success:
            await callback.message.edit_text(
                f"{E.SUCCESS} Часовой пояс успешно изменен на:\n<b>{tz}</b>\n\n"
                f"Теперь все время будет указываться в этом часовом поясе.",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                f"{E.ERROR} Ошибка при сохранении часового пояса", parse_mode="HTML")
    except pytz.UnknownTimeZoneError:
        await callback.message.edit_text(
            f"{E.ERROR} Неизвестный часовой пояс: {tz}", parse_mode="HTML")

    await callback.answer()


@router.callback_query(SettingsCB.filter())
# SettingsCB with action='back'.
# `edit_text` doesn't accept `ReplyKeyboardMarkup` (InlineKeyboardMarkup is expected).
# So we edit the message text (without reply_markup) and then send a new message
# with `get_admin_main_menu()` (the reply keyboard).
async def settings_back(callback: types.CallbackQuery, callback_data: dict | None = None):
    if callback_data is None:
        callback_data = SettingsCB.unpack(callback.data or "")

    # Try to delete the original message from chat
    try:
        await callback.message.delete()
    except Exception:
        try:
            await callback.message.edit_text(f"{E.HAND} Возврат в главное меню", reply_markup=None)
        except Exception:
            pass

    #await callback.message.answer("",reply_markup=get_admin_main_menu())
    await callback.message.answer(f"{E.CANCEL} Изменение часового пояса отменено")
    await callback.answer()