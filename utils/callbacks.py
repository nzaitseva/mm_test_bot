"""
Simple typed CallbackData factories using aiogram's pydantic-based API.
We intentionally drop fallback/aiogram v2 heuristics and require aiogram v3+ with
`CallbackData` that supports typed fields via pydantic (automatic type casting).
"""
import logging


try:
    from aiogram.utils.callback_data import CallbackData as _CB
except Exception:
    # Some aiogram installs expose CallbackData in `aiogram.filters.callback_data`
    from aiogram.filters.callback_data import CallbackData as _CB

logger = logging.getLogger(__name__)

# Typed factories: `test_id` is typed as int so parsing will yield int values
class SelectTestCB(_CB, prefix="select"):
    test_id: int

class DeleteTestCB(_CB, prefix="delete"):
    test_id: int

class ViewTestCB(_CB, prefix="view"):
    test_id: int

class StartEditCB(_CB, prefix="startedit"):
    test_id: int

class SessionEditCB(_CB, prefix="session"):
    test_id: int
    field: str

class SessionDoneCB(_CB, prefix="sessiondone"):
    test_id: int

class SessionCancelCB(_CB, prefix="sessioncancel"):
    test_id: int

class TestOptionCB(_CB, prefix="opt"):
    test_id: int
    option: str

class DetailBackCB(_CB, prefix="detailback"):
    test_id: int

class TimezoneCB(_CB, prefix="timezone"):
    tz: str

class DeleteScheduleCB(_CB, prefix="delschedule"):
    schedule_id: int

class ConfirmDeleteScheduleCB(_CB, prefix="confirmdelschedule"):
    schedule_id: int

class CancelDeleteScheduleCB(_CB, prefix="canceldelschedule"):
    schedule_id: int

class ConfirmDeleteTestCB(_CB, prefix="confirmdeltest"):
    test_id: int

class CancelDeleteTestCB(_CB, prefix="canceldeltest"):
    test_id: int

class SettingsCB(_CB, prefix="settings"):
    action: str

# В aiogram v3 нативный подход — это использование классов-наследников CallbackData
# (pydantic-моделей). Раньше проект использовал небольшой совместительный shim `_Factory`
# с методами `.new()` / `.parse()` для минимальных правок. Теперь мы удаляем shim
# и используем нативный API aiogram:
#  - Создание callback_data: `TimezoneCB(tz="open").pack()`
#  - Разбор callback_data: `inst = TimezoneCB.unpack(data); values = inst.model_dump()`
#  - Фильтр для роутера: `TimezoneCB.filter()`
#
# Это делает код более явным и полностью совместимым с aiogram v3.

# Экспортируем сами классы (см. объявления выше) и оставляем алиас CallbackData
# для совместимости с aiogram/внешними инструментами.
CallbackData = _CB  # type: ignore