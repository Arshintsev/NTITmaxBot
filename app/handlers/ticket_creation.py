from maxapi import Dispatcher
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from app.keyboards import MainMenuKeyboards, CreateTaskKeyboards
from app.states import TicketStates
from app.pyrus.client import get_themes_from_api
from app.pyrus.service import PyrusService
import re
import asyncio

# =========================
# PHONE VALIDATION
# =========================

PHONE_REGEX = re.compile(r'^(\+7|7|8)\D*\d{3}\D*\d{3}\D*\d{2}\D*\d{2}$')


def normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)

    if digits.startswith('8'):
        digits = '7' + digits[1:]

    if len(digits) == 10:
        digits = '7' + digits

    return f"+{digits[:11]}"


# =========================
# MAIN ROUTER
# =========================

def register_ticket_creation(dp: Dispatcher, pyrus_service: PyrusService):
    """FSM обработчики создания заявки"""

    # =========================
    # STEP 1 — INN
    # =========================

    @dp.message_created(TicketStates.AWAITING_INN)
    async def process_inn(event: MessageCreated, context: MemoryContext):
        if not event.message.body or not event.message.body.text:
            return

        inn = event.message.body.text.strip()

        if not inn or not inn.isdigit() or len(inn) not in (10, 12):
            await event.message.answer(
                "❌ Введите корректный ИНН (10 или 12 цифр):",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        # 🔥 НЕ блокируем event loop
        company_name = await pyrus_service.get_contractor_id_by_inn(inn)

        if company_name:
            # ✅ СОХРАНЯЕМ В STATE
            await context.update_data(
                inn=inn,
                company_name=company_name['name'],
                contractor_id=company_name['id']
            )

            await event.message.answer(
                f"✅ Найдена организация:\n"
                f"📛 {company_name}\n"
                f"🔢 ИНН: {inn}\n\n"
                f"📋 Теперь введите ваше ФИО:"
            )
        await context.update_data(inn=inn)
        await context.set_state(TicketStates.AWAITING_NAME)

        await event.message.answer(
            "📋 Введите ваше ФИО:",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    # =========================
    # STEP 2 — NAME
    # =========================

    @dp.message_created(TicketStates.AWAITING_NAME)
    async def process_name(event: MessageCreated, context: MemoryContext):
        if not event.message.body or not event.message.body.text:
            return

        name = event.message.body.text.strip()

        if not name:
            await event.message.answer(
                "❌ Введите имя:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        await context.update_data(name=name)
        await context.set_state(TicketStates.AWAITING_PHONE)

        await event.message.answer(
            "📱 Введите номер телефона:",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    # =========================
    # STEP 3 — PHONE
    # =========================

    @dp.message_created(TicketStates.AWAITING_PHONE)
    async def process_phone(event: MessageCreated, context: MemoryContext):
        if not event.message.body or not event.message.body.text:
            return

        phone = event.message.body.text.strip()

        if not phone:
            await event.message.answer(
                "❌ Введите номер телефона:",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        if not PHONE_REGEX.match(phone):
            await event.message.answer(
                "❌ Неверный формат телефона.\nПример: +79991234567",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        digits = re.sub(r'\D', '', phone)

        if len(digits) not in (10, 11):
            await event.message.answer(
                "❌ Некорректный номер телефона.",
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
            )
            return

        normalized_phone = normalize_phone(phone)

        await context.update_data(phone=normalized_phone)
        await context.set_state(TicketStates.AWAITING_PC_NAME)

        await event.message.answer(
            "💻 Введите имя компьютера:",
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()]
        )

    # =========================
    # STEP 4 — PC NAME
    # =========================

    @dp.message_created(TicketStates.AWAITING_PC_NAME)
    async def process_pc_name(event: MessageCreated, context: MemoryContext):
        pc_name = event.message.body.text.strip()

        if not pc_name:
            await event.message.answer("❌ Введите имя компьютера:")
            return

        await context.update_data(pc_name=pc_name)

        items = await get_themes_from_api()
        keyboard = await CreateTaskKeyboards.build_themes_task_keyboard(items)

        # ❗ ТОЛЬКО показываем темы, НЕ меняем state на PROBLEM
        await context.set_state(TicketStates.AWAITING_THEME)

        await event.message.answer(
            "📌 Выберите тему обращения:",
            attachments=[keyboard]
        )



    # =========================
    # STEP 5 — PROBLEM
    # =========================

    @dp.message_created(TicketStates.AWAITING_PROBLEM)
    async def process_problem(event: MessageCreated, context: MemoryContext):
        problem = event.message.body.text.strip()

        if not problem:
            await event.message.answer("❌ Опишите проблему:")
            return

        await context.update_data(problem=problem)

        data = await context.get_data()

        preview = (
            "📋 Предпросмотр заявки\n\n"
            f"📌 ИНН: {data.get('inn')}\n"
            f"👤 Контакт: {data.get('name')}\n"
            f"📱 Телефон: {data.get('phone')}\n"
            f"💻 ПК: {data.get('pc_name')}\n"
            f"🏷 Тема: {data.get('theme_name')}\n\n"
            f"❗ Проблема:\n{problem}"
        )

        await context.set_state(TicketStates.CONFIRMING_TICKET)

        await event.message.answer(
            preview,
            attachments=[MainMenuKeyboards.create_confirmation_keyboard()]
        )