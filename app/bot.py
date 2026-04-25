import asyncio
import logging
import os
from dotenv import load_dotenv

from maxapi import Bot, Dispatcher, F
from maxapi.types import (
    MessageCreated,
    MessageCallback,
    CommandStart,
    Command
)
from maxapi.context import MemoryContext
from keyboards import MainMenuKeyboards
from text import MainMenuMessages
from states import TicketStates, InfoStates
load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('MAX_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен бота не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher()



@dp.message_created(CommandStart())
@dp.message_created(Command('menu'))
async def start(event: MessageCreated, context: MemoryContext):
    """Показать главное меню и сбросить состояние"""
    await context.set_state(None)
    await context.clear()
    await event.message.answer(
    MainMenuMessages.WELCOME_MESSAGE,
        attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
    )


#  Текст БЕЗ активного состояния (None)
@dp.message_created(None)
async def handle_text_without_state(event: MessageCreated, context: MemoryContext):
    """Когда нет активного состояния - отправляем предупреждение"""

    if event.message.body.text and event.message.body.text.startswith('/'):
        return

    await event.message.answer(
        MainMenuMessages.NOT_IN_CHAT_MODE_MESSAGE,
        attachments=[MainMenuKeyboards.create_go_to_menu_keyboard()]
    )
@dp.message_created(Command('menu'))
async def menu(event: MessageCreated):
    """Команда /menu - показать главное меню"""
    await event.message.answer(
        MainMenuMessages.WELCOME_MESSAGE,
        attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
    )

#  ЭТОТ ОБРАБОТЧИК - ОН ЛОВИТ НАЖАТИЯ НА КНОПКИ
@dp.message_callback()
async def handle_callback(callback: MessageCallback):
    """Обработчик нажатий на CallbackButton"""

    # Получаем payload из нажатой кнопки
    button_payload = callback.callback.payload


    print(f"Нажата кнопка с payload: {button_payload}")  # Отладка в консоли

    # Если нажата кнопка "Наши контакты"
    if button_payload == 'contacts_info':
        # ✅ Показываем информацию о контактах + кнопку "Назад"
        await callback.answer()
        await callback.message.edit(
            text=MainMenuMessages.FEEDBACK_INFO_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )


    #Если нажата кнопка "О нас"
    elif button_payload == 'company_info':
        await callback.answer()
        await callback.message.edit(
            text=MainMenuMessages.COMPANY_INFO_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    # Если нажата кнопка "Назад"
    elif button_payload == 'back_to_main_menu':
        # ✅ Возвращаемся в главное меню
        await callback.answer()
        await callback.message.edit(
            text=MainMenuMessages.WELCOME_MESSAGE,
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
        )
    #elif button_payload == 'process_data':
    #elif button_payload == 'comment_task':
    #elif button_payload == 'cancel_request':
    #elif button_payload == 'closed_tasks':
async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())