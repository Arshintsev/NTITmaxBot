# states.py
from maxapi.context import StatesGroup, State


class TicketStates(StatesGroup):
    """Состояния для работы с заявками"""

    # === Создание заявки (6 шагов) ===
    AWAITING_INN = State()  # Шаг 1: Ожидание ввода ИНН
    AWAITING_CONFIRMATION = State()  # Шаг 2: Ожидание подтверждения организации
    AWAITING_NAME = State()  # Шаг 3: Ожидание ввода имени
    AWAITING_PHONE = State()  # Шаг 4: Ожидание ввода телефона
    AWAITING_PC_NAME = State()  # Шаг 5: Ожидание ввода имени ПК
    AWAITING_THEME = State()
    AWAITING_PROBLEM = State()  # Шаг 6: Ожидание описания проблемы
    CONFIRMING_TICKET = State()  # Шаг 7: Подтверждение создания заявки

    # === Комментарии ===
    SELECTING_TASK_FOR_COMMENT = State()  # Выбор задачи для комментария
    AWAITING_COMMENT_TEXT = State()  # Ожидание текста комментария

    # === Отмена заявки ===
    SELECTING_TASK_FOR_CANCEL = State()  # Выбор задачи для отмены
    CONFIRMING_CANCEL = State()  # Подтверждение отмены

    # === Прочее ===
    VIEWING_CLOSED_TASKS = State()  # Просмотр закрытых задач


class InfoStates(StatesGroup):
    """Состояния для просмотра информации"""
    VIEWING_CONTACTS = State()  # Просмотр контактов
    VIEWING_ABOUT = State()  # Просмотр информации о компании