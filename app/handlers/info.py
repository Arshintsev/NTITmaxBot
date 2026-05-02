# handlers/info.py
"""
Модуль для обработки информационных кнопок:
- Контакты
- О компании
- Закрытые задачи
"""

from maxapi.types import MessageCallback
from maxapi.context import MemoryContext
from app.keyboards import MainMenuKeyboards
from app.text import MainMenuMessages
from app.states import InfoStates, TicketStates


# from app.crm_api import get_user_closed_tasks  # Раскомментировать когда будет готова


class InfoHandlers:
    """Класс-контейнер для обработчиков информационных кнопок"""

    @staticmethod
    async def show_contacts(callback: MessageCallback, context: MemoryContext):
        """
        Показать контактную информацию.

        Args:
            callback: Объект callback запроса
            context: Контекст состояния пользователя
        """
        await callback.answer()
        await callback.message.edit(
            text=MainMenuMessages.FEEDBACK_INFO_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )


    @staticmethod
    async def show_about(callback: MessageCallback, context: MemoryContext):
        """
        Показать информацию о компании.

        Args:
            callback: Объект callback запроса
            context: Контекст состояния пользователя
        """
        await callback.answer()
        await callback.message.edit(
            text=MainMenuMessages.COMPANY_INFO_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    @staticmethod
    async def closed_tasks(callback: MessageCallback, context: MemoryContext):
        """
        Показать закрыте заявки за 24 часа.

        Args:
            callback: Объект callback запроса
            context: Контекст состояния пользователя
        """
        await callback.answer()
        await callback.message.edit(
            text="Задача 21 закрыта",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )


#  Создаем экземпляр для удобного импорта в callback_router
handle_info_callbacks = InfoHandlers()


