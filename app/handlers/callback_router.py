# handlers/callback_router.py
from maxapi import Dispatcher
from maxapi.types import MessageCallback
from maxapi.context import MemoryContext
from app.keyboards import MainMenuKeyboards
from app.text import MainMenuMessages
from app.states import TicketStates
from .info import handle_info_callbacks  # ✅ Импорт вашего экземпляра
from app.pyrus_client import check_inn_in_db, save_ticket


def register_callback_router(dp: Dispatcher):
    """Главный роутер для callback кнопок"""
    print("🔵 Регистрация callback_router...")
    @dp.message_callback()
    async def router(callback: MessageCallback, context: MemoryContext):
        print("🟢 CALLBACK ПОЛУЧЕН!")  # ← СЮДА (будет на каждое нажатие кнопки)
        payload = callback.callback.payload
        print(f"🔔 Payload: {payload}")  # ← СЮДА

        # ====== ИНФОРМАЦИЯ ======
        if payload == 'contacts_info':
            await handle_info_callbacks.show_contacts(callback, context)
            return

        if payload == 'company_info':
            await handle_info_callbacks.show_about(callback, context)
            return

        # ====== НАВИГАЦИЯ ======
        if payload == 'back_to_main_menu':

            await context.clear()
            await context.set_state(None)
            await callback.answer()
            await callback.message.edit(
                text=MainMenuMessages.WELCOME_MESSAGE,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
            )

            return

        # ====== СОЗДАНИЕ ЗАЯВКИ ======
        if payload == 'process_data':

            await context.clear()
            await context.set_state(TicketStates.AWAITING_INN)
            await callback.message.edit(
                text="🏢 **Создание обращения**\n\nШаг 1/6\n\nВведите **ИНН** вашей организации:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            await callback.answer()
            current_state = await context.get_state()
            print(f"📌 Текущее состояние: {current_state}")
            return

        if payload == 'confirm_continue':
            await context.set_state(TicketStates.AWAITING_NAME)
            await callback.message.edit(
                text="👤 **Шаг 2/6**\n\nВведите ваше **Имя и Фамилию**:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            await callback.answer()
            return

        if payload == 'submit_ticket':
            data = await context.get_data()
            ticket_data = {
                'user_id': callback.from_user.user_id,
                'inn': data.get('inn'),
                'company_name': data.get('company_name'),
                'name': data.get('name'),
                'phone': data.get('phone'),
                'pc_name': data.get('pc_name'),
                'problem': data.get('problem'),
            }
            ticket_id = save_ticket(ticket_data)
            await context.set_state(None)
            await context.clear()
            await callback.message.edit(
                f"✅ **Заявка #{ticket_id} успешно создана!**",
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
            )
            await callback.answer()
            return

        print(f"⚠️ Неизвестный payload: {payload}")
        await callback.answer()
    print("✅ callback_router зарегистрирован")  # ← И СЮДА