import tempfile
import asyncio
from types import SimpleNamespace
from datetime import datetime, timedelta
import pytz

from utils.database import Database
from utils.callbacks import (
    DeleteScheduleCB,
    ConfirmDeleteScheduleCB,
    CancelDeleteScheduleCB,
    ConfirmDeleteTestCB,
    CancelDeleteTestCB,
    DeleteTestCB,
)
from handlers.admin.main_handlers import (
    request_delete_schedule,
    confirm_delete_schedule,
    cancel_delete_schedule,
)
from handlers.admin.delete_handlers import (
    process_test_selection_for_deletion,
    confirm_test_deletion,
    cancel_test_deletion,
)
from utils.emoji import Emoji as E


class DummyMessage:
    def __init__(self):
        self.edited = []
        self.answered = False
        self.answered_msgs = []

    async def edit_text(self, text, parse_mode=None, reply_markup=None):
        self.edited.append((text, parse_mode, reply_markup))

    async def answer(self, *args, **kwargs):
        self.answered = True
        self.answered_msgs.append((args, kwargs))


class DummyCallback:
    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=123)
        self.message = DummyMessage()
        self.answered = False

    async def answer(self, *args, **kwargs):
        self.answered = True


def test_request_and_confirm_delete_schedule_flow():
    async def _inner():
        db_file = tempfile.NamedTemporaryFile(delete=False).name
        db = Database(db_file)

        # create test and schedule
        test_id = db.add_test("T", "text", "txt", None, None, "Q", {"A": "B"})
        assert isinstance(test_id, int)

        when = datetime.now(pytz.utc) + timedelta(minutes=1)
        db.add_schedule(test_id, "@chan", when)

        schedules = db.get_active_schedules()
        assert schedules
        schedule_id = schedules[0][0]

        # request delete
        cb = DummyCallback(DeleteScheduleCB(schedule_id=schedule_id).pack())
        await request_delete_schedule(cb, db)

        assert cb.message.edited, "message.edit_text should be called"
        text, _, reply_markup = cb.message.edited[-1]
        assert "Вы уверены" in text

        # find confirm button
        buttons = [b for row in reply_markup.inline_keyboard for b in row]
        cbs = [btn.callback_data for btn in buttons]
        assert ConfirmDeleteScheduleCB(schedule_id=schedule_id).pack() in cbs

        # confirm deletion
        cb2 = DummyCallback(ConfirmDeleteScheduleCB(schedule_id=schedule_id).pack())
        await confirm_delete_schedule(cb2, db)

        # schedule should be removed
        assert all(s[0] != schedule_id for s in db.get_active_schedules())

    asyncio.run(_inner())


def test_cancel_delete_schedule():
    async def _inner():
        db_file = tempfile.NamedTemporaryFile(delete=False).name
        db = Database(db_file)

        test_id = db.add_test("T", "text", "txt", None, None, "Q", {"A": "B"})
        when = datetime.now(pytz.utc) + timedelta(minutes=1)
        db.add_schedule(test_id, "@chan", when)
        schedule_id = db.get_active_schedules()[0][0]

        cb = DummyCallback(CancelDeleteScheduleCB(schedule_id=schedule_id).pack())
        await cancel_delete_schedule(cb)

        assert cb.message.edited[-1][0].startswith(E.CANCEL)

    asyncio.run(_inner())


def test_confirm_and_cancel_delete_test():
    async def _inner():
        db_file = tempfile.NamedTemporaryFile(delete=False).name
        db = Database(db_file)

        test_id = db.add_test("Title", "text", "Some text", None, None, "Q", {"A": "B"})

        # simulate pressing delete test -> process selection
        cb = DummyCallback(DeleteTestCB(test_id=test_id).pack())
        await process_test_selection_for_deletion(cb, db)

        # now confirm deletion
        cb2 = DummyCallback(ConfirmDeleteTestCB(test_id=test_id).pack())
        await confirm_test_deletion(cb2, db)

        assert all(t[0] != test_id for t in db.get_all_tests())

        # cancel test deletion (just verify message edit)
        cb3 = DummyCallback(CancelDeleteTestCB(test_id=test_id).pack())
        await cancel_test_deletion(cb3)
        assert cb3.message.edited[-1][0].startswith(E.CANCEL)

    asyncio.run(_inner())
