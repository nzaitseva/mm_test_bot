from aiogram import Router

# central admin router
router = Router()

# Import submodules (each defines its own Router) and include them into central router.
# Import order: main (menues) first, then feature modules.
from . import main_handlers  # noqa: F401
from . import create_handlers  # noqa: F401
from . import schedule_handlers  # noqa: F401
from . import delete_handlers  # noqa: F401
from . import view_edit_handlers  # noqa: F401

# include subrouters into the central router
router.include_router(main_handlers.router)
router.include_router(create_handlers.router)
router.include_router(schedule_handlers.router)
router.include_router(delete_handlers.router)
router.include_router(view_edit_handlers.router)