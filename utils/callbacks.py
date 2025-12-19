"""
Robust CallbackData factories.

This module tries to import CallbackData from common aiogram locations and
verifies that it behaves like the usual aiogram factory (callable returning
a factory/class with .new/.parse/.filter). If that fails, a small fallback
implementation is used which provides .new/.parse/.filter compatible API.

The goal: make the rest of the code work regardless of minor differences
between aiogram versions / environments, and avoid import-time TypeError.
"""
from typing import Callable, Dict, Any
import logging
import importlib

logger = logging.getLogger(__name__)

_CallbackFactory = None

def _try_import_candidate(module_name: str, attr_name: str):
    try:
        mod = importlib.import_module(module_name)
        attr = getattr(mod, attr_name, None)
        return attr
    except Exception:
        return None

# Candidate import paths to try (some environments expose it in different modules)
candidates = [
    ("aiogram.utils.callback_data", "CallbackData"),
    ("aiogram.filters.callback_data", "CallbackData"),
]

for modname, attr in candidates:
    Candidate = _try_import_candidate(modname, attr)
    if Candidate is None:
        continue

    # Test whether Candidate can be used as factory: try calling Candidate("name","field")
    try:
        test_factory = Candidate("testcb", "f1")
        # aiogram's CallbackData returns a class-like factory that provides .new/.parse/.filter
        has_new = hasattr(test_factory, "new")
        has_filter = hasattr(test_factory, "filter")
        if has_new and has_filter:
            _CallbackFactory = Candidate
            logger.debug("Using CallbackData from %s.%s", modname, attr)
            break
        else:
            # Candidate exists but doesn't provide expected API; skip
            logger.debug("Candidate CallbackData from %s.%s lacks expected API", modname, attr)
            continue
    except Exception as e:
        logger.debug("Candidate CallbackData from %s.%s not usable: %s", modname, attr, e)
        continue

# Fallback minimal implementation
if _CallbackFactory is None:
    logger.info("Falling back to CallbackData fallback implementation (aiogram CallbackData not usable)")

    class _CallbackDataFallback:
        def __init__(self, name: str, *parts: str):
            self.name = name
            self.parts = list(parts)

        def new(self, **kwargs) -> str:
            # encode as "name:key=val|key2=val2"
            pairs = []
            for p in self.parts:
                v = kwargs.get(p, "")
                sval = str(v).replace("|", " ").replace("=", " ")
                pairs.append(f"{p}={sval}")
            return f"{self.name}:" + "|".join(pairs)

        def parse(self, callback_data: str) -> Dict[str, str]:
            try:
                if not callback_data.startswith(self.name + ":"):
                    return {}
                _, rest = callback_data.split(":", 1)
                items = rest.split("|")
                res = {}
                for it in items:
                    if "=" in it:
                        k, v = it.split("=", 1)
                        res[k] = v
                return res
            except Exception as e:
                logger.exception("Failed to parse callback_data %r: %s", callback_data, e)
                return {}

        def filter(self) -> Callable[[Any], bool]:
            # Return simple predicate usable in router.callback_query(predicate)
            def _pred(callback):
                try:
                    data = getattr(callback, "data", None)
                    return isinstance(data, str) and data.startswith(self.name + ":")
                except Exception:
                    return False
            return _pred

    CallbackFactory = _CallbackDataFallback
else:
    # Use the real aiogram factory as CallbackFactory (callable)
    CallbackFactory = _CallbackFactory

# Create common factories used across the project
select_test_cb = CallbackFactory("select", "test_id")
delete_test_cb = CallbackFactory("delete", "test_id")
view_test_cb = CallbackFactory("view", "test_id")
start_edit_cb = CallbackFactory("startedit", "test_id")
session_edit_cb = CallbackFactory("session", "test_id", "field")
session_done_cb = CallbackFactory("sessiondone", "test_id")
session_cancel_cb = CallbackFactory("sessioncancel", "test_id")
test_option_cb = CallbackFactory("opt", "test_id", "option")

# Expose name for compatibility with code expecting CallbackData class-like object
CallbackData = CallbackFactory  # type: ignore