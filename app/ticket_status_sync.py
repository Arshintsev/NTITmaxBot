"""
Синхронизация статуса заявок с Pyrus → SQLite (открыта / «Решена»).
"""

import logging
from typing import Optional

from app.data.instance import db
from app.data.sqlite import (
    CLOSED_STATUSES,
    TICKET_CLOSED_STATUS,
    TICKET_OPEN_STATUS,
    is_ticket_closed,
)
from app.pyrus.models import PyrusTask
from app.pyrus.service import PyrusService

logger = logging.getLogger(__name__)


def _pyrus_task_is_closed(task: PyrusTask) -> bool:
    """Задача закрыта в Pyrus (только is_closed, без устаревшего close_date)."""
    inner = (task.raw_data or {}).get("task") or {}
    return inner.get("is_closed") is True


def resolve_status_from_pyrus(task: PyrusTask) -> str:
    """
    Статус для БД: закрыта в Pyrus → «Решена»;
    снова открыта в Pyrus → статус из формы или «Открыта».
    """
    form_status = (task.status or "").strip()
    if _pyrus_task_is_closed(task):
        return TICKET_CLOSED_STATUS

    if form_status and not is_ticket_closed(form_status):
        if form_status in CLOSED_STATUSES:
            return TICKET_OPEN_STATUS
        return form_status
    return TICKET_OPEN_STATUS


async def sync_ticket_status(
    pyrus_service: PyrusService, pyrus_task_id: int
) -> Optional[bool]:
    """
    Обновляет статус в БД по задаче Pyrus.
    Возвращает True, если заявка открыта (не «Решена»); None — нет доступа.
    """
    task = await pyrus_service.get_task_safe(pyrus_task_id)
    if task is None:
        http_status = await pyrus_service.get_task_http_status(pyrus_task_id)
        if http_status == 403:
            db.mark_pyrus_sync_blocked(pyrus_task_id)
        return None

    status = resolve_status_from_pyrus(task)
    db.update_ticket_status_from_pyrus(pyrus_task_id, status)
    if not is_ticket_closed(status):
        logger.debug("Заявка %s открыта в БД (статус: %s)", pyrus_task_id, status)
    return not is_ticket_closed(status)


async def sync_user_tickets(pyrus_service: PyrusService, max_user_id: int) -> None:
    """Синхронизирует все заявки пользователя из локальной БД."""
    for tid in db.list_pyrus_task_ids_by_user(max_user_id):
        await sync_ticket_status(pyrus_service, tid)


async def run_status_sync_cycle(pyrus_service: PyrusService) -> int:
    """Фоновая синхронизация: открытые и «Решена» (переоткрытие в Pyrus)."""
    updated = 0
    for row in db.list_tickets_for_status_sync():
        tid = int(row["pyrus_task_id"])
        result = await sync_ticket_status(pyrus_service, tid)
        if result is not None:
            updated += 1
    return updated
