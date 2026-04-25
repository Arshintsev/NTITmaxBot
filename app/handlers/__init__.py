# handlers/__init__.py
from .commands import register_commands
from .ticket_creation import register_ticket_creation
from .callback_router import register_callback_router


def register_all_handlers(dp):
    """Регистрация всех обработчиков"""
    print("🔵 Регистрация ВСЕХ обработчиков...")
    register_commands(dp)
    register_ticket_creation(dp)
    register_callback_router(dp)
    print("✅ Все обработчики зарегистрированы")