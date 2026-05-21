from maxapi import Dispatcher, F
from maxapi.types import MessageCallback
from maxapi.context import MemoryContext
import json
import logging

from app.keyboards import MainMenuKeyboards
from app.text import MainMenuMessages, CreateTaskMessages, TaskActionsMessages
from app.messages import ticket_preview_message, theme_selected_message
from app.states import TicketStates
from .info import handle_info_callbacks
from app.pyrus.service import PyrusService
from app.data.instance import db
from app.user_profile import (
    get_profile,
    has_complete_profile,
    profile_context_payload,
    save_profile_from_ticket_data,
)
logger = logging.getLogger(__name__)


def register_callback_router(dp: Dispatcher, pyrus_service: PyrusService):
    async def send_ticket_preview(callback: MessageCallback, context: MemoryContext):
        data = await context.get_data()
        preview = ticket_preview_message(data)

        await context.set_state(TicketStates.CONFIRMING_TICKET)
        await callback.message.answer(
            preview,
            attachments=[MainMenuKeyboards.create_confirmation_keyboard()],
        )

    @dp.message_callback(F.callback.payload == 'contacts_info')
    async def contacts(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await handle_info_callbacks.show_contacts(callback, context)

    @dp.message_callback(F.callback.payload == 'company_info')
    async def about(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await handle_info_callbacks.show_about(callback, context)

    @dp.message_callback(F.callback.payload == 'back_to_main_menu')
    async def back(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()

        await callback.message.edit(
            text=MainMenuMessages.WELCOME_MESSAGE,
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
        )

    @dp.message_callback(F.callback.payload == 'process_data')
    async def start_ticket(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()

        user_id = callback.from_user.user_id
        if has_complete_profile(user_id):
            profile = get_profile(user_id)
            if profile:
                await context.update_data(**profile_context_payload(profile))
            await context.set_state(TicketStates.AWAITING_INN)
            await callback.message.edit(
                text=CreateTaskMessages.INPUT_DATA_MESSAGE,
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
            )
            return

        await callback.message.edit(
            text=CreateTaskMessages.INPUT_USER_DATA,
            attachments=[MainMenuKeyboards.create_pre_inn_keyboard()],
        )

    @dp.message_callback(F.callback.payload == 'start_inn_input')
    async def start_inn_input(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()

        user_id = callback.from_user.user_id
        profile = get_profile(user_id)
        if profile:
            await context.update_data(**profile_context_payload(profile))

        await context.set_state(TicketStates.AWAITING_INN)

        await callback.message.edit(
            text=CreateTaskMessages.INPUT_DATA_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )

    @dp.message_callback(F.callback.payload.startswith("theme_sel:"))
    async def select_theme(callback: MessageCallback, context: MemoryContext):
        await callback.answer()

        item_id = callback.callback.payload.removeprefix("theme_sel:").strip()
        data = dict(await context.get_data())
        labels = data.get("theme_labels_by_item_id") or {}
        theme_name = labels.get(item_id) or labels.get(str(item_id)) or "Тема"

        await context.update_data(theme_id=item_id, theme_name=theme_name)
        await context.set_state(TicketStates.AWAITING_PROBLEM)

        await callback.message.answer(
            text=theme_selected_message(theme_name),
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )

    @dp.message_callback(F.callback.payload.startswith("theme:"))
    async def select_theme_legacy(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        parts = callback.callback.payload.split(":", 2)
        if len(parts) < 3:
            return
        _, item_id, value = parts
        await context.update_data(theme_id=item_id, theme_name=value)
        await context.set_state(TicketStates.AWAITING_PROBLEM)
        await callback.message.answer(
            text=theme_selected_message(value),
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )

    @dp.message_callback(F.callback.payload == 'attach_yes')
    async def attach_yes(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.update_data(attachments=[])
        await context.set_state(TicketStates.AWAITING_ATTACHMENTS)
        await callback.message.answer(
            CreateTaskMessages.ADD_FILES_MESSAGE,
            attachments=[MainMenuKeyboards.create_attachment_upload_keyboard()],
        )

    @dp.message_callback(F.callback.payload == 'attach_no')
    async def attach_no(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.update_data(attachments=[])
        await send_ticket_preview(callback, context)

    @dp.message_callback(F.callback.payload == 'attach_reset')
    async def attach_reset(callback: MessageCallback, context: MemoryContext):
        await callback.answer(TaskActionsMessages.CORRECT_CLEAR_FILES_MESSAGE)
        await context.update_data(attachments=[])
        await callback.message.answer(
            CreateTaskMessages.PROCESS_CORRECT_FILES_DONE_MESSAGE,
            attachments=[MainMenuKeyboards.create_attachment_upload_keyboard()],
        )

    @dp.message_callback(F.callback.payload == 'attach_send')
    async def attach_send(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await send_ticket_preview(callback, context)

    @dp.message_callback(F.callback.payload == 'confirm_action')
    async def confirm(callback: MessageCallback, context: MemoryContext):
        await callback.answer()

        data = dict(await context.get_data())
        data["user_id"] = callback.from_user.user_id

        required = ["inn", "name", "phone", "pc_name", "theme_id", "problem"]

        if not all(data.get(k) for k in required):
            await context.clear()
            await callback.message.edit(
                CreateTaskMessages.MESSAGE_CREATE_TASK_ERROR,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
            return

        try:
            ensured_client_id = await pyrus_service.ensure_client_for_ticket(data)
        except Exception:
            await callback.message.edit(
                TaskActionsMessages.SERVER_ERROR_MESSAGE,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
            return

        if ensured_client_id:
            data["client_task_id"] = ensured_client_id

        try:
            ticket_id = await pyrus_service.create_task(data)
        except Exception:
            await callback.message.edit(
                CreateTaskMessages.MESSAGE_CREATE_TASK_ERROR,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
            return

        save_profile_from_ticket_data(
            max_user_id=callback.from_user.user_id,
            data=data,
            max_username=getattr(callback.from_user, "username", None),
            max_full_name=getattr(callback.from_user, "name", None),
        )

        db.create_or_update_ticket(
            pyrus_task_id=ticket_id,
            max_user_id=callback.from_user.user_id,
            status="Новая",
            inn=data.get("inn"),
            theme_id=data.get("theme_id"),
            theme_name=data.get("theme_name"),
            subject=f"Заявка от {data.get('name')}",
            phone=data.get("phone"),
            pc_name=data.get("pc_name"),
            problem=data.get("problem"),
            company_name=data.get("company_name"),
            contractor_id=data.get("contractor_id"),
            client_task_id=data.get("client_task_id"),
            payload_json=json.dumps(data, ensure_ascii=False),
        )

        await context.clear()

        await callback.message.edit(
            CreateTaskMessages.format_post_task_message(ticket_id),
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
        )

    @dp.message_callback(F.callback.payload.startswith("eng_rating:"))
    async def engineer_rating(callback: MessageCallback, context: MemoryContext):
        parts = callback.callback.payload.split(":")
        if len(parts) != 3 or parts[0] != "eng_rating":
            await callback.answer()
            return
        try:
            tid = int(parts[1])
            rating = int(parts[2])
        except ValueError:
            await callback.answer()
            return
        if rating not in (1, 2, 3, 4, 5):
            await callback.answer()
            return

        user_id = callback.from_user.user_id
        ticket = db.get_ticket_by_pyrus_for_user(tid, user_id)
        if not ticket:
            await callback.answer("Нет доступа к заявке.")
            return
        if db.has_ticket_rating(tid):
            await callback.answer("Оценка уже сохранена.")
            return

        pyrus_ok = await pyrus_service.submit_user_rating(tid, rating, user_id)

        try:
            db.save_ticket_rating(
                pyrus_task_id=tid,
                max_user_id=user_id,
                rating=rating,
                engineer_name=None,
                comment=None,
            )
        except ValueError:
            await callback.answer("Ошибка.")
            return

        await callback.answer("Спасибо!")
        thanks = CreateTaskMessages.set_mark_message(rating)
        if not pyrus_ok:
            thanks += (
                "\n\n⚠️ Оценка сохранена в боте, но в Pyrus не записана "
                "(нет доступа к задаче или не удалось заполнить поля оценки)."
            )
        await callback.message.answer(thanks)

    @dp.message_callback(F.callback.payload == 'cancel_action')
    async def cancel(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()

        await callback.message.edit(
            MainMenuMessages.COMMAND_CANCEL_TEXT,
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
        )
