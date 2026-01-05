from aiogram import Router
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message()
async def debug_message(message):
    # Log message body for debugging (do not reply to user)
    logger.info(f"[debug_router] message from {message.from_user.id}: text={message.text!r} keys={list(message.__dict__.keys())}")


@router.callback_query()
async def debug_callback(callback):
    logger.info(f"[debug_router] callback from {callback.from_user.id}: data={callback.data!r}")
    # Answer callback to prevent client spinner if this is the last handler
    try:
        await callback.answer()
    except Exception:
        pass