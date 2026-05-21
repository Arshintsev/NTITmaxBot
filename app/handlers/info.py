"""
Информационные кнопки: контакты, о компании, недавно закрытые заявки.
"""

from maxapi import Dispatcher, F
from maxapi.types import MessageCallback
from maxapi.context import MemoryContext

from app.config import settings
from app.data.instance import db
from app.keyboards import MainMenuKeyboards, TaskActionsKeyboards
from app.messages import RECENTLY_CLOSED_TASKS_HEADER
from app.pyrus.service import PyrusService
from app.states import TicketStates
from app.text import MainMenuMessages, ClosedTasksTexts
from app.data.sqlite import TICKET_OPEN_STATUS
from app.ticket_status_sync import sync_ticket_status, sync_user_tickets


class InfoHandlers:
    @staticmethod
    async def show_contacts(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await callback.message.edit(
            text=MainMenuMessages.FEEDBACK_INFO_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )

    @staticmethod
    async def show_about(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await callback.message.edit(
            text=MainMenuMessages.COMPANY_INFO_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )


def register_info_handlers(dp: Dispatcher, pyrus_service: PyrusService):
    @dp.message_callback(F.callback.payload == "closed_tasks")
    async def recently_closed_tasks(
        callback: MessageCallback, context: MemoryContext
    ):
        await callback.answer()
        await context.clear()
        user_id = callback.from_user.user_id
        await sync_user_tickets(pyrus_service, user_id)
        tickets = db.get_recently_closed_tickets_by_user(
            user_id, hours=settings.RECENTLY_CLOSED_HOURS
        )
        if not tickets:
            await callback.message.edit(
                text=ClosedTasksTexts.NOT_FOUND_CLOSED_TASKS_TEXT,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
            return

        await context.set_state(TicketStates.VIEWING_CLOSED_TASKS)
        await callback.message.edit(
            text=RECENTLY_CLOSED_TASKS_HEADER,
            attachments=[
                TaskActionsKeyboards.create_recently_closed_keyboard(tickets)
            ],
        )

    @dp.message_callback(F.callback.payload.startswith("reopen_sel:"))
    async def reopen_closed_task(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        try:
            tid = int(callback.callback.payload.removeprefix("reopen_sel:"))
        except ValueError:
            return

        user_id = callback.from_user.user_id
        ticket = db.get_ticket_by_pyrus_for_user(tid, user_id)
        if not ticket:
            await callback.message.answer(ClosedTasksTexts.ERROR_OPEN_TASK_TEXT)
            return
        if db.is_ticket_open_for_user(tid, user_id):
            await callback.message.answer(
                "ℹ️ Заявка уже открыта.",
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
            return

        ok = await pyrus_service.reopen_task_by_user(tid, user_id)
        await context.clear()
        if ok:
            synced = await sync_ticket_status(pyrus_service, tid)
            if synced is None:
                db.update_ticket_status_from_pyrus(tid, TICKET_OPEN_STATUS)
            await callback.message.edit(
                text=ClosedTasksTexts.SUCCESS_OPEN_TASK,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
        else:
            await callback.message.edit(
                text=ClosedTasksTexts.ERROR_OPEN_TASK_TEXT,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )


handle_info_callbacks = InfoHandlers()
