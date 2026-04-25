# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (ЗАГЛУШКИ) ==========
def get_user_active_tasks(user_id: int) -> list:
    """Получить активные задачи пользователя (заглушка)"""
    return [
        {'id': 1, 'title': 'Проблема с оплатой', 'status': 'active'},
        {'id': 2, 'title': 'Техническая поддержка', 'status': 'active'},
        {'id': 3, 'title': 'Вопрос по документации', 'status': 'active'},
    ]


def get_user_closed_tasks(user_id: int) -> list:
    """Получить закрытые задачи пользователя (заглушка)"""
    return [
        {'id': 100, 'title': 'Создание аккаунта', 'status': 'closed'},
        {'id': 101, 'title': 'Настройка бота', 'status': 'closed'},
    ]


def save_ticket(user_id: int, text: str) -> int:
    """Сохранить новую заявку (заглушка)"""
    import random
    ticket_id = random.randint(1000, 9999)
    print(f"✅ Создана заявка #{ticket_id} от {user_id}: {text}")
    return ticket_id


def save_comment(task_id: int, user_id: int, text: str) -> None:
    """Сохранить комментарий к задаче (заглушка)"""
    print(f"💬 Комментарий к задаче #{task_id} от {user_id}: {text}")


def cancel_task(task_id: int, user_id: int) -> None:
    """Отменить задачу (заглушка)"""
    print(f"❌ Задача #{task_id} отменена пользователем {user_id}")

def check_inn_in_db(inn_number: str) -> bool:
    """Проверка существования ИНН в базе CRM (тестовый стенд)"""
    valid_inns = {"1", "7701010101", "7712345678"}
    return inn_number in valid_inns