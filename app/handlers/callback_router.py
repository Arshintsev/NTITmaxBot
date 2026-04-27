from maxapi import Dispatcher, F
from maxapi.types import MessageCallback
from maxapi.context import MemoryContext

from app.keyboards import MainMenuKeyboards
from app.text import MainMenuMessages
from app.states import TicketStates
from .info import handle_info_callbacks
from app.pyrus.client import save_ticket

import asyncio


def register_callback_router(dp: Dispatcher):

    # ================= INFO =================

    @dp.message_callback(F.callback.payload == 'contacts_info')
    async def contacts(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await handle_info_callbacks.show_contacts(callback, context)

    @dp.message_callback(F.callback.payload == 'company_info')
    async def about(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await handle_info_callbacks.show_about(callback, context)

    # ================= NAVIGATION =================

    @dp.message_callback(F.callback.payload == 'back_to_main_menu')
    async def back(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()

        await callback.message.edit(
            text=MainMenuMessages.WELCOME_MESSAGE,
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
        )

    # ================= START FLOW =================

    @dp.message_callback(F.callback.payload == 'process_data')
    async def start_ticket(callback: MessageCallback, context: MemoryContext):
        await callback.answer()

        await context.clear()

        await callback.message.edit(
            text=(
                "⚠️ Перед началом заполните данные.\n\n"
                "▶️ Нажмите «Информация прочитана» или вернитесь в меню."
            ),
            attachments=[MainMenuKeyboards.create_pre_inn_keyboard()]
        )

    @dp.message_callback(F.callback.payload == 'start_inn_input')
    async def start_inn_input(callback: MessageCallback, context: MemoryContext):
        await callback.answer()

        await context.clear()
        await context.set_state(TicketStates.AWAITING_INN)

        await callback.message.edit(
            text="🏢 Введите ИНН:",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    # ================= THEME =================

    @dp.message_callback(F.callback.payload.startswith("theme:"))
    async def select_theme(callback: MessageCallback, context: MemoryContext):
        await callback.answer()

        _, item_id, value = callback.callback.payload.split(":", 2)

        await context.update_data(
            theme_id=item_id,
            theme_name=value
        )

        # 👉 теперь только после выбора темы идём дальше
        await context.set_state(TicketStates.AWAITING_PROBLEM)

        await callback.message.answer(
            text=f"📌 Тема: {value}\n\n📝 Теперь опишите проблему:",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    # ================= CONFIRM =================

    @dp.message_callback(F.callback.payload == 'confirm_action')
    async def confirm(callback: MessageCallback, context: MemoryContext):
        await callback.answer()

        data = dict(await context.get_data())
        data["user_id"] = callback.from_user.user_id

        required = ["inn", "name", "phone", "pc_name", "theme_id", "problem"]

        if not all(data.get(k) for k in required):
            await context.clear()

            await callback.message.edit(
                "❌ Ошибка: не все данные заполнены",
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
            )
            return

        ticket_id = await asyncio.to_thread(save_ticket, data)

        await context.clear()

        await callback.message.edit(
            f"✅ Заявка #{ticket_id} создана",
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
        )

    # ================= CANCEL =================

    @dp.message_callback(F.callback.payload == 'cancel_action')
    async def cancel(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()

        await callback.message.edit(
            "❌ Отменено",
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()]
        )