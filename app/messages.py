"""
Сборка сообщений только из констант и методов texts/ (без правок texts/).
"""

from app.formatting import escape_markdown
from texts.create_task import CreateTaskMessages
from texts.task_actions import TaskActionsMessages


def contractor_found_message(_company_name: str, _inn: str) -> str:
    """После найденного ИНН — текст из texts/create_task.py."""
    return CreateTaskMessages.INPUT_FULLNAME_MESSAGE


def theme_selected_message(_theme_name: str) -> str:
    return CreateTaskMessages.INPUT_PROBLEM_MESSAGE


def ticket_preview_message(data: dict) -> str:
    return TaskActionsMessages.get_task_data_message(
        task_id=escape_markdown(str(data.get("inn") or "—")),
        problem=escape_markdown(str(data.get("theme_name") or "—")),
        description=escape_markdown(str(data.get("problem") or "—")),
    )


TICKET_NOT_OPEN_MESSAGE = (
    "⚠️ Эта заявка уже закрыта. "
    "Комментировать и отменять можно только **открытые** обращения."
)

RECENTLY_CLOSED_TASKS_HEADER = (
    "📋 **Недавно закрытые задачи** (за последний час):"
)


def inn_validation_message(inn: str) -> str:
    if not inn:
        return CreateTaskMessages.INN_EMPTY_MESSAGE
    if not inn.isdigit():
        return CreateTaskMessages.INN_LONG_MESSAGE
    if len(inn) < 10:
        return CreateTaskMessages.INN_SHORT_MESSAGE
    return CreateTaskMessages.INN_LONG_MESSAGE
