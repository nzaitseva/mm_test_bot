# handlers/settings_handlers.py
import pytz
import logging

from aiogram import Router, F, types

from utils.emoji import Emoji as E
from utils.database import Database
from utils.config import load_config
from filters.admin_filters import IsAdminFilter
from keyboards.keyboards import get_settings_keyboard, get_timezone_keyboard, get_admin_main_menu
from utils.callbacks import TimezoneCB, SettingsCB

# NOTE (RU): раньше использовался `.new()`/`.parse()` shim; теперь используем нативный
# aiogram v3 подход: `TimezoneCB(...).pack()` и `TimezoneCB.unpack(data)`


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
# NOTE (RU): используем нативный `unpack` для разбора callback-data, когда aiogram
# не инжектит объект автоматически. Этот обработчик отвечает только за открытие
# списка часовых поясов (tz == "open").
async def show_timezone_settings(callback: types.CallbackQuery, db: Database, callback_data: dict | None = None):
    if callback_data is None:
        # Разбираем данные через native `unpack` (вернет инстанс CallbackData)
        callback_data = TimezoneCB.unpack(callback.data or "")

    # support both dict (from .parse()) and typed model injected by aiogram
    if isinstance(callback_data, dict):
        tz_val = callback_data.get("tz")
    elif hasattr(callback_data, "model_dump"):
        tz_val = callback_data.model_dump().get("tz")
    else:
        tz_val = getattr(callback_data, "tz", None)

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
        # Разбираем данные через native `unpack` (вернет инстанс CallbackData)
        callback_data = TimezoneCB.unpack(callback.data or "")

    # support both dict and typed model
    if isinstance(callback_data, dict):
        tz = callback_data.get("tz")
    elif hasattr(callback_data, "model_dump"):
        tz = callback_data.model_dump().get("tz")
    else:
        tz = getattr(callback_data, "tz", None)

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
# NOTE (RU): раньше использовался legacy callback 'settings_back'; теперь используем
# нативный класс SettingsCB с action='back'.
# Важно: `edit_text` не принимает `ReplyKeyboardMarkup` (ожидается InlineKeyboardMarkup).
# Поэтому мы редактируем текст сообщения (без reply_markup), а затем отправляем новое
# сообщение с `get_admin_main_menu()` (reply-клавиатурой).
async def settings_back(callback: types.CallbackQuery, callback_data: dict | None = None):
    if callback_data is None:
        # Разбираем callback (если aiogram не инжектил модель)
        callback_data = SettingsCB.unpack(callback.data or "")

    # Попытаемся удалить исходное сообщение, чтобы не оставлять его в чате.
    try:
        await callback.message.delete()
    except Exception:
        # Если удаление невозможно (например, недостаточно прав), попробуем просто
        # отредактировать сообщение и убрать inline-кнопки.
        try:
            await callback.message.edit_text(f"{E.HAND} Возврат в главное меню", reply_markup=None)
        except Exception:
            # silent fallback — ничего не делаем
            pass

    # Отправляем новое сообщение с reply-клавиатурой (главное меню)
    await callback.message.answer("Главное меню:", reply_markup=get_admin_main_menu())

    await callback.answer()