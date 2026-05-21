"""
Уведомление в MAX при закрытии заявки в Pyrus и запрос оценки 1–5.
Только фоновый опрос — не при /start и не при входе в меню.
"""

import asyncio
import logging
from typing import Optional

from maxapi import Bot

from app.config import settings
from app.data.instance import db
from app.keyboards import RatingKeyboards
from app.pyrus.service import PyrusService
from app.text import CreateTaskMessages
from app.data.sqlite import is_ticket_closed
from app.ticket_status_sync import resolve_status_from_pyrus

logger = logging.getLogger(__name__)


async def send_closure_and_rating_request(
    bot: Bot,
    *,
    max_user_id: int,
    pyrus_task_id: int,
    theme_name: Optional[str],
) -> None:
    problem_type = (theme_name or "").strip() or "—"
    completion = CreateTaskMessages.get_completion_task_message(
        int(pyrus_task_id),
        problem_type,
    )
    await bot.send_message(user_id=max_user_id, text=completion)
    await bot.send_message(
        user_id=max_user_id,
        text=CreateTaskMessages.CHECK_QUALITY_MESSAGE,
        attachments=[RatingKeyboards.create_engineer_rating_keyboard(pyrus_task_id)],
    )


async def try_notify_closed_ticket(
    bot: Bot,
    pyrus_service: PyrusService,
    *,
    pyrus_task_id: int,
    max_user_id: int,
    theme_name: Optional[str],
) -> bool:
    if db.has_ticket_rating(pyrus_task_id) or db.is_closure_notified(pyrus_task_id):
        return False

    task = await pyrus_service.get_task_safe(pyrus_task_id)
    if task is None:
        status = await pyrus_service.get_task_http_status(pyrus_task_id)
        if status == 403:
            db.mark_pyrus_sync_blocked(pyrus_task_id)
        return False

    status = resolve_status_from_pyrus(task)
    db.update_ticket_status_from_pyrus(pyrus_task_id, status)
    if not is_ticket_closed(status):
        return False

    try:
        await send_closure_and_rating_request(
            bot,
            max_user_id=max_user_id,
            pyrus_task_id=pyrus_task_id,
            theme_name=theme_name,
        )
    except Exception:
        logger.exception(
            "Не удалось отправить уведомление о закрытии в MAX, user=%s task=%s",
            max_user_id,
            pyrus_task_id,
        )
        return False

    db.mark_closure_notified(pyrus_task_id)
    logger.info(
        "Уведомление о закрытии #%s отправлено пользователю MAX %s",
        pyrus_task_id,
        max_user_id,
    )
    return True


async def run_closure_poll_cycle(bot: Bot, pyrus_service: PyrusService) -> int:
    from app.ticket_status_sync import run_status_sync_cycle

    await run_status_sync_cycle(pyrus_service)
    sent = 0
    for row in db.list_tickets_pending_closure_notification():
        if await try_notify_closed_ticket(
            bot,
            pyrus_service,
            pyrus_task_id=int(row["pyrus_task_id"]),
            max_user_id=int(row["max_user_id"]),
            theme_name=row.get("theme_name"),
        ):
            sent += 1
    return sent


async def closure_poll_loop(bot: Bot, pyrus_service: PyrusService) -> None:
    interval = max(30, settings.CLOSURE_POLL_INTERVAL_SECONDS)
    logger.info("Фоновая проверка закрытых заявок Pyrus (интервал %s с)", interval)
    while True:
        try:
            sent = await run_closure_poll_cycle(bot, pyrus_service)
            if sent:
                logger.info("Уведомлений о закрытии за цикл: %s", sent)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка цикла проверки закрытых заявок")
        await asyncio.sleep(interval)
