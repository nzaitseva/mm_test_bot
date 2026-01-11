import logging

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

class FieldCancelCB(_CB, prefix="fieldcancel"):
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


# Export the classes themselves and leave the CallbackData alias
# for compatibility with aiogram/external tools.
CallbackData = _CB  # type: ignore

def get_callback_value(callback_data, key: str):
    """Return the value for `key` from callback_data supporting multiple formats.

    Supports:
      - dict (old .parse() code style)
      - pydantic-model (aiogram CallbackData instances) — `.model_dump()`
      - object with attribute (getattr)

    """
    if callback_data is None:
        return None
    if isinstance(callback_data, dict):
        return callback_data.get(key)
    if hasattr(callback_data, "model_dump"):
        try:
            return callback_data.model_dump().get(key)
        except Exception:
            return None
    return getattr(callback_data, key, None)


def get_int_callback_value(callback_data, key: str):
    val = get_callback_value(callback_data, key)
    try:
        return int(val) if val is not None else None
    except Exception:
        return None