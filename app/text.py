"""
Единая точка доступа к текстам из папки texts/.

Файлы в texts/ не редактируются. Неиспользуемые константы и методы
оставлены для будущих сценариев (комментарии, оценки, закрытие задач и т.д.).
"""

from texts.closed_tasks import ClosedTasksTexts
from texts.create_task import CreateTaskMessages
from texts.main_menu import MainMenuMessages
from texts.task_actions import TaskActionsMessages

__all__ = [
    "MainMenuMessages",
    "CreateTaskMessages",
    "TaskActionsMessages",
    "ClosedTasksTexts",
]
