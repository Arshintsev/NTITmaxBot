# handlers/__init__.py
from .commands import register_commands
from .ticket_creation import register_ticket_creation
from .callback_router import register_callback_router
from .task_actions import register_task_actions
from .info import register_info_handlers


def register_all_handlers(dp, pyrus_service):
    """Регистрация всех обработчиков"""
    print("🔵 Регистрация ВСЕХ обработчиков...")
    register_commands(dp, pyrus_service)
    register_ticket_creation(dp, pyrus_service)
    register_task_actions(dp, pyrus_service)
    register_info_handlers(dp, pyrus_service)
    register_callback_router(dp, pyrus_service)
    print("✅ Все обработчики зарегистрированы")