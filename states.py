from aiogram.fsm.state import State, StatesGroup

class TestCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_content_type = State()
    waiting_for_text_content = State()
    waiting_for_photo = State()
    waiting_for_question = State()
    waiting_for_options = State()

class ScheduleCreation(StatesGroup):
    waiting_for_test_selection = State()
    waiting_for_channel = State()
    waiting_for_time = State()

class TestDeletion(StatesGroup):
    waiting_for_test_selection = State()
    waiting_for_confirmation = State()

class ScheduleDeletion(StatesGroup):
    waiting_for_schedule_selection = State()
    waiting_for_confirmation = State()

class EditTest(StatesGroup):
    waiting_for_new_title = State()
    waiting_for_new_text = State()
    waiting_for_new_photo = State()
    waiting_for_new_question = State()
    waiting_for_new_options = State()

class EditSession(StatesGroup):
    choosing_field = State()
    waiting_for_value = State()