# handlers/ticket_creation.py (исправленный)
from maxapi import Dispatcher
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from app.keyboards import MainMenuKeyboards
from app.states import TicketStates
from app.pyrus_client import check_inn_in_db, save_ticket


def register_ticket_creation(dp: Dispatcher):
    """Регистрация FSM обработчиков создания заявки (только текст)"""

    # === ОБРАБОТЧИКИ ТЕКСТОВЫХ СООБЩЕНИЙ (FSM) ===

    @dp.message_created(TicketStates.AWAITING_INN)
    async def process_inn(event: MessageCreated, context: MemoryContext):
        """Обработка введенного ИНН"""
        inn = event.message.body.text.strip()

        if not inn:
            await event.message.answer(
                "❌ Пожалуйста, введите ИНН:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        company_data = check_inn_in_db(inn)

        if company_data:
            await context.update_data(inn=inn, company_name=company_data['name'])
            await event.message.answer(
                f"✅ **Организация найдена:**\n\n"
                f"🏢 {company_data['name']}\n"
                f"📍 {company_data['address']}\n\n"
                f"Верно?",
                attachments=[MainMenuKeyboards.create_confirm_keyboard()]
            )
            await context.set_state(TicketStates.AWAITING_CONFIRMATION)
        else:
            await event.message.answer(
                f"❌ **Организация с ИНН {inn} не найдена.**\n\n"
                f"Попробуйте еще раз или вернитесь в меню:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )

    @dp.message_created(TicketStates.AWAITING_NAME)
    async def process_name(event: MessageCreated, context: MemoryContext):
        """Обработка введенного имени"""
        name = event.message.body.text.strip()
        if not name:
            await event.message.answer(
                "❌ Пожалуйста, введите ваше имя:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        await context.update_data(name=name)
        await context.set_state(TicketStates.AWAITING_PHONE)
        await event.message.answer(
            "📱 **Шаг 3/6**\n\nВведите ваш **Номер телефона**:",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    @dp.message_created(TicketStates.AWAITING_PHONE)
    async def process_phone(event: MessageCreated, context: MemoryContext):
        """Обработка введенного телефона"""
        phone = event.message.body.text.strip()
        if not phone:
            await event.message.answer(
                "❌ Пожалуйста, введите номер телефона:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        await context.update_data(phone=phone)
        await context.set_state(TicketStates.AWAITING_PC_NAME)
        await event.message.answer(
            "💻 **Шаг 4/6**\n\nВведите **Имя компьютера**:",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    @dp.message_created(TicketStates.AWAITING_PC_NAME)
    async def process_pc_name(event: MessageCreated, context: MemoryContext):
        """Обработка введенного имени ПК"""
        pc_name = event.message.body.text.strip()
        if not pc_name:
            await event.message.answer(
                "❌ Пожалуйста, введите имя компьютера:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        await context.update_data(pc_name=pc_name)
        await context.set_state(TicketStates.AWAITING_PROBLEM)
        await event.message.answer(
            "📝 **Шаг 5/6**\n\n**Опишите проблему:**\n\n"
            "- Что случилось?\n"
            "- Когда произошло?\n"
            "- Есть ли ошибки?",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    @dp.message_created(TicketStates.AWAITING_PROBLEM)
    async def process_problem(event: MessageCreated, context: MemoryContext):
        """Обработка описания проблемы"""
        problem = event.message.body.text.strip()
        if not problem:
            await event.message.answer(
                "❌ Пожалуйста, опишите проблему:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        await context.update_data(problem=problem)
        data = await context.get_data()

        preview = (
            "📋 **Предпросмотр заявки**\n\n"
            f"🏢 Организация: {data.get('company_name', 'Не указано')}\n"
            f"📌 ИНН: {data.get('inn', 'Не указан')}\n"
            f"👤 Контактное лицо: {data.get('name', 'Не указано')}\n"
            f"📱 Телефон: {data.get('phone', 'Не указан')}\n"
            f"💻 Имя ПК: {data.get('pc_name', 'Не указано')}\n\n"
            f"❗ **Описание проблемы:**\n{problem}\n\n"
            f"Проверьте данные. Если всё верно - нажмите кнопку 'Оформить заявку'."
        )

        await context.set_state(TicketStates.CONFIRMING_TICKET)
        await event.message.answer(
            preview,
            attachments=[MainMenuKeyboards.create_submit_ticket_keyboard()]
        )