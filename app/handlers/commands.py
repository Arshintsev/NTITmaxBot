from maxapi import Dispatcher
from maxapi.types import MessageCreated, CommandStart, Command
from maxapi.context import MemoryContext
from app.keyboards import MainMenuKeyboards
from app.text import MainMenuMessages


def register_commands(dp: Dispatcher):
    """Регистрация обработчиков команд"""

    @dp.message_created(CommandStart())
    @dp.message_created(Command('menu'))
    async def show_menu(event: MessageCreated, context: MemoryContext):
        """Показать главное меню и сбросить состояние"""
        await context.set_state(None)
        await context.clear()
        await event.message.answer(
            MainMenuMessages.WELCOME_MESSAGE,
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
        )

    @dp.message_created(Command('cancel'))
    async def cancel_action(event: MessageCreated, context: MemoryContext):
        """Отмена текущего действия"""
        await context.set_state(None)
        await context.clear()
        await event.message.answer(
            "❌ Действие отменено.",
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
        )

    @dp.message_created(None)
    async def handle_text_without_state(event: MessageCreated, context: MemoryContext):
        """Когда нет активного состояния - отправляем предупреждение"""
        if event.message.body.text and event.message.body.text.startswith('/'):
            return

        await event.message.answer(
            MainMenuMessages.NOT_IN_CHAT_MODE_MESSAGE,
            attachments=[MainMenuKeyboards.create_go_to_menu_keyboard()]
        )