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


    # @staticmethod
    # async def show_closed_tasks(callback: MessageCallback, context: MemoryContext):
    #     """
    #     Показать список закрытых задач пользователя.
    #
    #     Args:
    #         callback: Объект callback запроса
    #         context: Контекст состояния пользователя
    #     """
    #     user_id = callback.from_user.user_id
    #     await context.set_state(TicketStates.VIEWING_CLOSED_TASKS)
    #
    #     # Временная заглушка (потом заменить на реальный запрос к CRM)
    #     closed_tasks = []  # get_user_closed_tasks(user_id)
    #
    #     if closed_tasks:
    #         tasks_list = []
    #         for task in closed_tasks:
    #             tasks_list.append(f"✅ #{task['id']}: {task['title']}")
    #
    #         tasks_text = "\n".join(tasks_list)
    #         message = f"📁 **Закрытые задачи**\n\n{tasks_text}"
    #     else:
    #         message = "📁 **Закрытые задачи**\n\nУ вас пока нет закрытых задач."
    #
    #     await callback.message.edit(
    #         text=message,
    #         attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
    #     )
    #     await callback.answer()


#  Создаем экземпляр для удобного импорта в callback_router
handle_info_callbacks = InfoHandlers()


