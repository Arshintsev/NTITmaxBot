
from maxapi.context import StatesGroup, State


class MainMenuStates(StatesGroup):
    """Главное меню (нет активного состояния)"""
    NONE = State()  # Фактически None


class TicketStates(StatesGroup):
    """Состояния для работы с заявками"""
    CREATING_TICKET = State()              # Ожидание текста новой заявки
    SELECTING_TASK_FOR_COMMENT = State()   # Выбор задачи для комментария
    ADDING_COMMENT = State()               # Ожидание текста комментария
    SELECTING_TASK_FOR_CANCEL = State()    # Выбор задачи для отмены
    CONFIRMING_CANCEL = State()            # Подтверждение отмены
    VIEWING_CLOSED_TASKS = State()         # Просмотр закрытых задач


class InfoStates(StatesGroup):
    """Состояния для просмотра информации"""
    VIEWING_CONTACTS = State()             # Просмотр контактов
    VIEWING_ABOUT = State()                # Просмотр информации о компании