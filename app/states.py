from aiogram.fsm.state import StatesGroup, State


class Login(StatesGroup):
    token = State()
    name_vikunja = State()

# class Task(StatesGroup):
#     chat_id = State
#     task_id = State()
#     bucke_id = State()
class Newsletter(StatesGroup):
    message = State()