import asyncio
import logging
import os
from dotenv import load_dotenv
from app.handlers import register_all_handlers

from maxapi import Bot, Dispatcher, F
from maxapi.types import (
    MessageCreated,
    MessageCallback,
)
from maxapi.context import MemoryContext
from keyboards import MainMenuKeyboards
from text import MainMenuMessages
from states import TicketStates, InfoStates
from pyrus_client import (
    save_ticket,
    save_comment,
    cancel_task,
    get_user_active_tasks,
    get_user_closed_tasks,
)
load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('MAX_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен бота не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryContext)

register_all_handlers(dp)


# ========== ОБРАБОТЧИКИ CALLBACK КНОПОК ==========

# @dp.message_callback()
# async def handle_callback(callback: MessageCallback, context: MemoryContext):
#     """Обработчик нажатий на CallbackButton"""
#
#     # Получаем payload из нажатой кнопки
#     button_payload = callback.callback.payload
#
#
#     print(f"Нажата кнопка с payload: {button_payload}")  # Отладка в консоли
#
#     # Если нажата кнопка "Наши контакты"
#     if button_payload == 'contacts_info':
#         # ✅ Показываем информацию о контактах + кнопку "Назад"
#         await callback.answer()
#         await callback.message.edit(
#             text=MainMenuMessages.FEEDBACK_INFO_MESSAGE,
#             attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
#         )
#
#
#     #Если нажата кнопка "О нас"
#     elif button_payload == 'company_info':
#         await callback.answer()
#         await callback.message.edit(
#             text=MainMenuMessages.COMPANY_INFO_MESSAGE,
#             attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
#         )
#
#     # Если нажата кнопка "Назад"
#     elif button_payload == 'back_to_main_menu':
#         # ✅ Возвращаемся в главное меню
#         await context.set_state(None)
#         await callback.answer()
#         await callback.message.edit(
#             text=MainMenuMessages.WELCOME_MESSAGE,
#             attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
#         )
#     elif button_payload == 'process_data':
#         await context.set_state(TicketStates.AWAITING_INN)
#         await callback.answer()
#         await callback.message.edit(
#             text="📝 **Создание обращения**\n\nОпишите вашу проблему текстовым сообщением:",
#             attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
#         )
#
#     #elif button_payload == 'comment_task':
#     #elif button_payload == 'cancel_request':
#     #elif button_payload == 'closed_tasks':

async def main():
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())