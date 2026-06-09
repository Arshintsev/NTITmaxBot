from maxapi import Dispatcher
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from app.keyboards import MainMenuKeyboards, CreateTaskKeyboards
from app.states import TicketStates
from app.pyrus.service import PyrusService
from app.messages import contractor_found_message, inn_validation_message
from app.text import CreateTaskMessages
from app.user_profile import (
    get_profile,
    has_complete_profile,
    profile_context_payload,
    save_profile,
    save_profile_from_ticket_data,
    ticket_start_context_payload,
)
import re

PHONE_REGEX = re.compile(r'^(\+7|7|8)\D*\d{3}\D*\d{3}\D*\d{2}\D*\d{2}$')


def normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)

    if digits.startswith('8'):
        digits = '7' + digits[1:]

    if len(digits) == 10:
        digits = '7' + digits

    return f"+{digits[:11]}"


def _extract_attachments_from_message(message_body) -> list[dict]:
    """Достаёт список вложений из входящего сообщения."""
    raw_items = []
    for attr in ("attachments", "files", "medias"):
        value = getattr(message_body, attr, None)
        if isinstance(value, list):
            raw_items.extend(value)

    def _find_first_url(data: dict) -> str | None:
        direct_url = data.get("url") or data.get("link") or data.get("download_url")
        if direct_url:
            return direct_url
        for nested_key in ("payload", "file", "document", "media"):
            nested = data.get(nested_key)
            if isinstance(nested, dict):
                nested_url = nested.get("url") or nested.get("link") or nested.get("download_url")
                if nested_url:
                    return nested_url
        return None

    extracted = []
    for item in raw_items:
        if hasattr(item, "model_dump"):
            data = item.model_dump()
        elif isinstance(item, dict):
            data = item
        elif hasattr(item, "__dict__"):
            data = dict(item.__dict__)
        else:
            continue

        url = _find_first_url(data)
        if not url:
            continue

        display_name = _attachment_display_name(data)
        extracted.append({"url": url, "name": display_name})
    return extracted


def _attachment_display_name(data: dict) -> str:
    for key in ("filename", "file_name", "name", "title"):
        v = data.get(key)
        if v and str(v).strip():
            return str(v).strip()

    for nested_key in ("payload", "file", "document", "media"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            for key in ("filename", "file_name", "name", "title"):
                v = nested.get(key)
                if v and str(v).strip():
                    return str(v).strip()

    ctype = (
        data.get("content_type")
        or data.get("mime_type")
        or data.get("mime")
    )
    if isinstance(ctype, str) and "jpeg" in ctype.lower():
        return "image.jpg"
    if isinstance(ctype, str) and "png" in ctype.lower():
        return "image.png"
    if isinstance(ctype, str) and "webp" in ctype.lower():
        return "image.webp"
    if isinstance(ctype, str) and "gif" in ctype.lower():
        return "image.gif"

    att_type = str(data.get("type", "") or data.get("kind", "") or "").lower()
    if att_type in ("photo", "image", "picture"):
        return "photo.jpg"
    if att_type == "png":
        return "image.png"

    return "Файл"


async def go_to_theme_selection(
    reply,
    context: MemoryContext,
    pyrus_service: PyrusService,
) -> None:
    """Переход к выбору темы. reply — async (text, attachments=...)."""
    data = await context.get_data()
    contractor_id = data.get("contractor_id")
    name = data.get("name")
    if name and contractor_id:
        client = await pyrus_service.get_client_info(name, contractor_id)
        if client:
            update_payload: dict = {}
            if client.get("id"):
                update_payload["client_task_id"] = client.get("id")
            if client.get("fio"):
                update_payload["name"] = client.get("fio")
            if update_payload:
                await context.update_data(**update_payload)

    items = await pyrus_service.get_themes()
    theme_labels = {
        str(it["item_id"]): str((it.get("values") or [""])[0])
        for it in items
        if it.get("item_id") is not None
    }
    await context.update_data(theme_labels_by_item_id=theme_labels)

    keyboard = await CreateTaskKeyboards.build_themes_task_keyboard(items)
    await context.set_state(TicketStates.AWAITING_THEME)

    await reply(
        CreateTaskMessages.CHOOSE_THEME_TASK_MESSAGE,
        attachments=[keyboard],
    )


async def continue_after_saved_company(
    *,
    user_id: int,
    context: MemoryContext,
    pyrus_service: PyrusService,
    reply,
) -> None:
    """После известного ИНН — сразу ФИО или выбор темы."""
    profile = get_profile(user_id)
    if profile:
        await context.update_data(**ticket_start_context_payload(profile))

    if has_complete_profile(user_id):
        await go_to_theme_selection(reply, context, pyrus_service)
        return

    await context.set_state(TicketStates.AWAITING_NAME)
    await reply(
        CreateTaskMessages.INPUT_FULLNAME_MESSAGE,
        attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
    )


def register_ticket_creation(dp: Dispatcher, pyrus_service: PyrusService):
    @dp.message_created(TicketStates.AWAITING_INN)
    async def process_inn(event: MessageCreated, context: MemoryContext):
        if not event.message.body or not event.message.body.text:
            return

        inn = event.message.body.text.strip()

        if not inn or not inn.isdigit() or len(inn) not in (10, 12):
            await event.message.answer(
                inn_validation_message(inn),
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
            )
            return

        contractor = await pyrus_service.get_contractor_info(inn)

        if contractor:
            user_id = event.from_user.user_id
            await context.update_data(
                inn=inn,
                company_name=contractor.get("name"),
                contractor_id=contractor.get("id"),
            )
            save_profile(
                max_user_id=user_id,
                inn=inn,
                company_name=contractor.get("name"),
                pyrus_contractor_task_id=contractor.get("id"),
                max_username=getattr(event.from_user, "username", None),
                max_full_name=getattr(event.from_user, "name", None),
            )
            data = await context.get_data()

            # Уже есть ФИО/телефон/ПК в сессии или в БД — не показываем повторно запрос ФИО
            if data.get("name") and data.get("phone") and data.get("pc_name"):
                await go_to_theme_selection(
                    event.message.answer, context, pyrus_service
                )
                return
            if has_complete_profile(user_id):
                profile = get_profile(user_id)
                if profile:
                    await context.update_data(**profile_context_payload(profile))
                await go_to_theme_selection(
                    event.message.answer, context, pyrus_service
                )
                return

            company_name = contractor.get("name") or "—"
            await event.message.answer(
                contractor_found_message(company_name, inn),
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
            )
            await context.set_state(TicketStates.AWAITING_NAME)
            return

        await context.update_data(inn=inn)
        await event.message.answer(
            CreateTaskMessages.NOT_FOUND_DATA_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )
        return

    @dp.message_created(TicketStates.AWAITING_NAME)
    async def process_name(event: MessageCreated, context: MemoryContext):
        if not event.message.body or not event.message.body.text:
            return

        name = event.message.body.text.strip()

        if not name:
            await event.message.answer(
                CreateTaskMessages.INPUT_FULLNAME_MESSAGE,
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
            )
            return

        current_data = await context.get_data()
        contractor_id = current_data.get("contractor_id")
        client = await pyrus_service.get_client_info(name, contractor_id)

        update_payload = {"name": name}
        if client:
            update_payload["client_task_id"] = client.get("id")
            if client.get("fio"):
                update_payload["name"] = client.get("fio")

        await context.update_data(**update_payload)
        save_profile(
            max_user_id=event.from_user.user_id,
            contact_name=update_payload.get("name"),
            max_username=getattr(event.from_user, "username", None),
            max_full_name=getattr(event.from_user, "name", None),
        )
        await context.set_state(TicketStates.AWAITING_PHONE)

        await event.message.answer(
            CreateTaskMessages.PHONE_INPUT_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )

    @dp.message_created(TicketStates.AWAITING_PHONE)
    async def process_phone(event: MessageCreated, context: MemoryContext):
        if not event.message.body or not event.message.body.text:
            return

        phone = event.message.body.text.strip()

        if not phone:
            await event.message.answer(
                CreateTaskMessages.MESSAGE_PHONE_EMPTY,
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
            )
            return

        if not PHONE_REGEX.match(phone):
            await event.message.answer(
                CreateTaskMessages.MESSAGE_PHONE_INVALID_FORMAT,
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
            )
            return

        digits = re.sub(r'\D', '', phone)

        if len(digits) not in (10, 11):
            await event.message.answer(
                CreateTaskMessages.MESSAGE_PHONE_TOO_SHORT,
                attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
            )
            return

        normalized_phone = normalize_phone(phone)

        await context.update_data(phone=normalized_phone)
        current_data = await context.get_data()
        save_profile(
            max_user_id=event.from_user.user_id,
            contact_name=current_data.get("name"),
            phone=normalized_phone,
            max_username=getattr(event.from_user, "username", None),
            max_full_name=getattr(event.from_user, "name", None),
        )
        await context.set_state(TicketStates.AWAITING_PC_NAME)

        await event.message.answer(
            CreateTaskMessages.INPUT_NAME_PC_MESSAGE,
            attachments=[MainMenuKeyboards.create_back_to_menu_keyboard()],
        )

    @dp.message_created(TicketStates.AWAITING_PC_NAME)
    async def process_pc_name(event: MessageCreated, context: MemoryContext):
        pc_name = event.message.body.text.strip()

        if not pc_name:
            await event.message.answer(CreateTaskMessages.MESSAGE_PC_NAME_EMPTY)
            return

        await context.update_data(pc_name=pc_name)
        current_data = await context.get_data()
        save_profile_from_ticket_data(
            max_user_id=event.from_user.user_id,
            data=current_data,
            max_username=getattr(event.from_user, "username", None),
            max_full_name=getattr(event.from_user, "name", None),
        )
        await go_to_theme_selection(event.message.answer, context, pyrus_service)

    @dp.message_created(TicketStates.AWAITING_PROBLEM)
    async def process_problem(event: MessageCreated, context: MemoryContext):
        problem = event.message.body.text.strip()

        if not problem:
            await event.message.answer(CreateTaskMessages.INPUT_PROBLEM_MESSAGE)
            return

        await context.update_data(problem=problem)
        await context.set_state(TicketStates.AWAITING_ATTACH_DECISION)

        await event.message.answer(
            CreateTaskMessages.IS_ATTACH_FILES_MESSAGE,
            attachments=[MainMenuKeyboards.create_attachment_decision_keyboard()],
        )

    @dp.message_created(TicketStates.AWAITING_ATTACHMENTS)
    async def process_attachments(event: MessageCreated, context: MemoryContext):
        if not event.message.body:
            return

        new_attachments = _extract_attachments_from_message(event.message.body)
        if not new_attachments:
            await event.message.answer(
                CreateTaskMessages.MESSAGE_NOT_FILES_FOR_CREATE_TASK,
                attachments=[MainMenuKeyboards.create_attachment_upload_keyboard()],
            )
            return

        current_data = await context.get_data()
        existing = current_data.get("attachments", [])
        merged = existing + new_attachments

        seen = set()
        unique_attachments = []
        for item in merged:
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            unique_attachments.append(item)

        await context.update_data(attachments=unique_attachments)
        await event.message.answer(
            CreateTaskMessages.PROCESS_CORRECT_FILES_DONE_MESSAGE,
            attachments=[MainMenuKeyboards.create_attachment_upload_keyboard()],
        )
