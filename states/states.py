from aiogram.fsm.state import State, StatesGroup

class QuickPauseStates(StatesGroup):
    waiting_purpose = State()
    waiting_time = State()
    confirmation = State()

class DailyCheckStates(StatesGroup):
    waiting_reflection = State()
    waiting_practice = State()