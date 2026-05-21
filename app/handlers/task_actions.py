from maxapi import Dispatcher, F
from maxapi.types import MessageCallback, MessageCreated
from maxapi.context import MemoryContext

from app.data.instance import db
from app.data.sqlite import TICKET_CLOSED_STATUS
from app.keyboards import MainMenuKeyboards, TaskActionsKeyboards
from app.messages import TICKET_NOT_OPEN_MESSAGE
from app.pyrus.service import PyrusService
from app.states import TicketStates
from app.text import CreateTaskMessages, MainMenuMessages, TaskActionsMessages
from app.handlers.ticket_creation import _extract_attachments_from_message
from app.ticket_status_sync import sync_ticket_status, sync_user_tickets

MIN_COMMENT_LEN = 2
MAX_COMMENT_LEN = 2000


async def _show_open_tasks(
    callback: MessageCallback,
    context: MemoryContext,
    pyrus_service: PyrusService,
    *,
    payload_prefix: str,
    next_state,
) -> bool:
    """Показывает список открытых заявок. False — нечего показывать."""
    user_id = callback.from_user.user_id
    await sync_user_tickets(pyrus_service, user_id)
    tickets = db.get_open_tickets_by_user(user_id)
    if not tickets:
        await callback.message.edit(
            text=TaskActionsMessages.NOT_FOUND_TASKS_MESSAGE,
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
        )
        return False

    await context.set_state(next_state)
    await callback.message.edit(
        text=TaskActionsMessages.SHOW_TASKS_MESSAGE,
        attachments=[
            TaskActionsKeyboards.create_open_tasks_keyboard(
                tickets, payload_prefix=payload_prefix
            )
        ],
    )
    return True


def register_task_actions(dp: Dispatcher, pyrus_service: PyrusService):
    @dp.message_callback(F.callback.payload == "comment_task")
    async def start_comment(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()
        await _show_open_tasks(
            callback,
            context,
            pyrus_service,
            payload_prefix="comment_sel",
            next_state=TicketStates.SELECTING_TASK_FOR_COMMENT,
        )

    @dp.message_callback(F.callback.payload.startswith("comment_sel:"))
    async def comment_select_task(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        try:
            tid = int(callback.callback.payload.removeprefix("comment_sel:"))
        except ValueError:
            return

        user_id = callback.from_user.user_id
        if not db.get_ticket_by_pyrus_for_user(tid, user_id):
            await callback.message.answer(TaskActionsMessages.TASK_ERROR_MESSAGE)
            return
        await sync_ticket_status(pyrus_service, tid)
        if not db.is_ticket_open_for_user(tid, user_id):
            await callback.message.answer(TICKET_NOT_OPEN_MESSAGE)
            return

        await context.update_data(pyrus_task_id=tid, comment_text="", attachments=[])
        await context.set_state(TicketStates.AWAITING_COMMENT_TEXT)
        await callback.message.edit(
            text=TaskActionsMessages.WRITE_TEXT_MESSAGE,
            attachments=[TaskActionsKeyboards.create_comment_prompt_keyboard()],
        )

    @dp.message_callback(F.callback.payload == "comment_skip")
    async def comment_skip_text(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.update_data(comment_text="")
        await context.set_state(TicketStates.AWAITING_COMMENT_ATTACHMENTS)
        await callback.message.edit(
            text=TaskActionsMessages.ADD_FILES_MESSAGE,
            attachments=[TaskActionsKeyboards.create_comment_attachment_keyboard()],
        )

    @dp.message_created(TicketStates.AWAITING_COMMENT_TEXT)
    async def comment_enter_text(event: MessageCreated, context: MemoryContext):
        if not event.message.body or not event.message.body.text:
            await event.message.answer(TaskActionsMessages.EMPTY_COMMENT_MESSAGE)
            return

        text = event.message.body.text.strip()
        if len(text) < MIN_COMMENT_LEN:
            await event.message.answer(
                TaskActionsMessages.SHORT_COMMENT_MESSAGE,
                attachments=[TaskActionsKeyboards.create_comment_prompt_keyboard()],
            )
            return
        if len(text) > MAX_COMMENT_LEN:
            await event.message.answer(
                TaskActionsMessages.LONG_COMMENT_MESSAGE,
                attachments=[TaskActionsKeyboards.create_comment_prompt_keyboard()],
            )
            return

        await context.update_data(comment_text=text, attachments=[])
        await context.set_state(TicketStates.AWAITING_COMMENT_ATTACHMENTS)
        await event.message.answer(
            TaskActionsMessages.ADD_FILES_MESSAGE,
            attachments=[TaskActionsKeyboards.create_comment_attachment_keyboard()],
        )

    @dp.message_created(TicketStates.AWAITING_COMMENT_ATTACHMENTS)
    async def comment_collect_files(event: MessageCreated, context: MemoryContext):
        if not event.message.body:
            return

        new_attachments = _extract_attachments_from_message(event.message.body)
        if not new_attachments:
            await event.message.answer(
                CreateTaskMessages.MESSAGE_NOT_FILES_FOR_CREATE_TASK,
                attachments=[TaskActionsKeyboards.create_comment_attachment_keyboard()],
            )
            return

        data = await context.get_data()
        existing = data.get("attachments", [])
        merged = existing + new_attachments
        seen: set[str] = set()
        unique: list[dict] = []
        for item in merged:
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(item)

        await context.update_data(attachments=unique)
        await event.message.answer(
            TaskActionsMessages.PROCESS_CORRECT_FILES_DONE_MESSAGE,
            attachments=[TaskActionsKeyboards.create_comment_attachment_keyboard()],
        )

    @dp.message_callback(F.callback.payload == "comment_attach_reset")
    async def comment_attach_reset(callback: MessageCallback, context: MemoryContext):
        await callback.answer(TaskActionsMessages.CORRECT_CLEAR_FILES_MESSAGE)
        await context.update_data(attachments=[])
        await callback.message.answer(
            TaskActionsMessages.PROCESS_CORRECT_FILES_DONE_MESSAGE,
            attachments=[TaskActionsKeyboards.create_comment_attachment_keyboard()],
        )

    @dp.message_callback(F.callback.payload == "comment_attach_send")
    async def comment_attach_send(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        data = dict(await context.get_data())
        tid = data.get("pyrus_task_id")
        if not tid:
            await callback.message.answer(TaskActionsMessages.TASK_ERROR_MESSAGE)
            return

        user_id = callback.from_user.user_id
        if not db.get_ticket_by_pyrus_for_user(int(tid), user_id):
            await callback.message.answer(TaskActionsMessages.TASK_ERROR_MESSAGE)
            return
        if not db.is_ticket_open_for_user(int(tid), user_id):
            await callback.message.answer(TICKET_NOT_OPEN_MESSAGE)
            return

        text = (data.get("comment_text") or "").strip()
        attachments = data.get("attachments") or []
        if not text and not attachments:
            await callback.message.answer(
                TaskActionsMessages.EMPTY_COMMENT_MESSAGE,
                attachments=[TaskActionsKeyboards.create_comment_attachment_keyboard()],
            )
            return

        await callback.message.answer(TaskActionsMessages.WAIT_CREATE_COMMENT_MESSAGE)
        ok = await pyrus_service.submit_task_comment(
            int(tid),
            text=text,
            attachments=attachments,
            max_user_id=user_id,
        )
        await context.clear()

        if ok:
            await callback.message.answer(
                TaskActionsMessages.POST_MESSAGE_TEXT,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
        else:
            await callback.message.answer(
                TaskActionsMessages.SERVER_ERROR_MESSAGE,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )

    @dp.message_callback(F.callback.payload == "cancel_request")
    async def start_cancel(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()
        await _show_open_tasks(
            callback,
            context,
            pyrus_service,
            payload_prefix="cancel_sel",
            next_state=TicketStates.SELECTING_TASK_FOR_CANCEL,
        )

    @dp.message_callback(F.callback.payload.startswith("cancel_sel:"))
    async def cancel_select_task(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        try:
            tid = int(callback.callback.payload.removeprefix("cancel_sel:"))
        except ValueError:
            return

        user_id = callback.from_user.user_id
        if not db.get_ticket_by_pyrus_for_user(tid, user_id):
            await callback.message.answer(TaskActionsMessages.TASK_ERROR_MESSAGE)
            return
        await sync_ticket_status(pyrus_service, tid)
        if not db.is_ticket_open_for_user(tid, user_id):
            await callback.message.answer(TICKET_NOT_OPEN_MESSAGE)
            return

        await context.update_data(pyrus_task_id=tid)
        await context.set_state(TicketStates.CONFIRMING_CANCEL)
        await callback.message.edit(
            text=f"Вы уверены, что хотите отменить обращение №{tid}?",
            attachments=[TaskActionsKeyboards.create_cancel_confirm_keyboard(tid)],
        )

    @dp.message_callback(F.callback.payload.startswith("confirm_cancel_task:"))
    async def confirm_cancel_task(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        try:
            tid = int(callback.callback.payload.removeprefix("confirm_cancel_task:"))
        except ValueError:
            return

        user_id = callback.from_user.user_id
        if not db.get_ticket_by_pyrus_for_user(tid, user_id):
            await callback.message.answer(TaskActionsMessages.TASK_ERROR_MESSAGE)
            return
        await sync_ticket_status(pyrus_service, tid)
        if not db.is_ticket_open_for_user(tid, user_id):
            await callback.message.answer(TICKET_NOT_OPEN_MESSAGE)
            return

        ok = await pyrus_service.close_task_by_user(tid, user_id)
        await context.clear()

        if ok:
            db.update_ticket_status_from_pyrus(tid, TICKET_CLOSED_STATUS)
            await callback.message.edit(
                text=TaskActionsMessages.CLOSE_TASK_TEXT,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )
        else:
            await callback.message.edit(
                text=TaskActionsMessages.CLOSE_FAILED,
                attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
            )

    @dp.message_callback(F.callback.payload == "cancel_task_abort")
    async def abort_cancel_task(callback: MessageCallback, context: MemoryContext):
        await callback.answer()
        await context.clear()
        await callback.message.edit(
            text=MainMenuMessages.WELCOME_MESSAGE,
            attachments=[MainMenuKeyboards.create_main_menu_keyboard()],
        )
