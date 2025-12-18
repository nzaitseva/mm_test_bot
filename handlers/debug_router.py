from aiogram import Router, F
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message()
async def debug_message(message):
    # Логируем всё тело сообщения для удобства отладки (не спамим пользователя)
    logger.info(f"[debug_router] message from {message.from_user.id}: text={message.text!r} keys={list(message.__dict__.keys())}")


@router.callback_query()
async def debug_callback(callback):
    logger.info(f"[debug_router] callback from {callback.from_user.id}: data={callback.data!r}")
    # Нельзя забывать отвечать на callback - если это последний обработчик, ответим, чтобы клиент не висел
    try:
        await callback.answer()
    except Exception:
        pass