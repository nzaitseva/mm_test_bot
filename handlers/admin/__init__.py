from aiogram import Router

from . import main_handlers
from . import create_handlers
from . import schedule_handlers
from . import delete_handlers
from . import view_edit_handlers

# Create a central admin router with attached specific routers
router = Router()

router.include_router(main_handlers.router)
router.include_router(create_handlers.router)
router.include_router(schedule_handlers.router)
router.include_router(delete_handlers.router)
router.include_router(view_edit_handlers.router)