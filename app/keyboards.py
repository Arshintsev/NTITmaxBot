from maxapi.types.attachments.buttons import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from texts.closed_tasks import ClosedTasksTexts


class MainMenuKeyboards:

    @staticmethod
    def create_main_menu_keyboard():
        builder = InlineKeyboardBuilder()

        builder.row(
            CallbackButton(text="📝 Создать обращение", payload="process_data")
        )
        builder.row(
            CallbackButton(text="💬 Комментарий", payload="comment_task"),
            CallbackButton(text="❌ Отмена заявки", payload="cancel_request"),
        )
        builder.row(
            CallbackButton(
                text="📁 Недавно закрытые задачи",
                payload="closed_tasks",
            )
        )
        builder.row(
            CallbackButton(text="📞 Контакты", payload="contacts_info"),
            CallbackButton(text="ℹ️ О нас", payload="company_info"),
        )
        return builder.as_markup()

    @staticmethod
    def create_back_to_menu_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="🔙 Вернуться в меню", payload="back_to_main_menu")
        )
        return builder.as_markup()

    @staticmethod
    def create_confirmation_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="✅ Подтвердить", payload="confirm_action"),
            CallbackButton(text="❌ Отмена", payload="cancel_action"),
        )
        return builder.as_markup()

    @staticmethod
    def create_go_to_menu_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(
                text=ClosedTasksTexts.MAIN_MENU_TEXT,
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()

    @staticmethod
    def create_pre_inn_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="✅ Информация прочитана", payload="start_inn_input")
        )
        builder.row(
            CallbackButton(
                text=ClosedTasksTexts.MAIN_MENU_TEXT,
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()

    @staticmethod
    def create_attachment_decision_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="✅ Да", payload="attach_yes"),
            CallbackButton(text="❌ Нет", payload="attach_no"),
        )
        builder.row(
            CallbackButton(
                text=ClosedTasksTexts.MAIN_MENU_TEXT,
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()

    @staticmethod
    def create_attachment_upload_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="📨 Отправить", payload="attach_send"),
            CallbackButton(text="🧹 Сбросить файлы", payload="attach_reset"),
        )
        builder.row(
            CallbackButton(
                text="🏠 Вернуться в главное меню",
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()


class TaskActionsKeyboards:
    """Список открытых заявок, комментарий, подтверждение отмены."""

    @staticmethod
    def _task_button_label(ticket: dict) -> str:
        tid = ticket.get("pyrus_task_id")
        theme = (ticket.get("theme_name") or ticket.get("subject") or "Обращение").strip()
        if len(theme) > 40:
            theme = theme[:37] + "..."
        return f"№{tid} — {theme}"

    @classmethod
    def create_open_tasks_keyboard(
        cls, tickets: list[dict], *, payload_prefix: str
    ):
        builder = InlineKeyboardBuilder()
        for ticket in tickets:
            tid = ticket.get("pyrus_task_id")
            if tid is None:
                continue
            builder.row(
                CallbackButton(
                    text=cls._task_button_label(ticket),
                    payload=f"{payload_prefix}:{int(tid)}",
                )
            )
        builder.row(
            CallbackButton(
                text=ClosedTasksTexts.MAIN_MENU_TEXT,
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()

    @staticmethod
    def create_comment_prompt_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="➡️ Пропустить", payload="comment_skip")
        )
        builder.row(
            CallbackButton(
                text=ClosedTasksTexts.MAIN_MENU_TEXT,
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()

    @staticmethod
    def create_comment_attachment_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            CallbackButton(text="📨 Отправить комментарий", payload="comment_attach_send"),
            CallbackButton(text="🧹 Сбросить файлы", payload="comment_attach_reset"),
        )
        builder.row(
            CallbackButton(
                text="🏠 Вернуться в главное меню",
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()

    @classmethod
    def create_recently_closed_keyboard(cls, tickets: list[dict]):
        builder = InlineKeyboardBuilder()
        for ticket in tickets:
            tid = ticket.get("pyrus_task_id")
            if tid is None:
                continue
            builder.row(
                CallbackButton(
                    text=f"{ClosedTasksTexts.OPEN_TASK_TEXT} {cls._task_button_label(ticket)}",
                    payload=f"reopen_sel:{int(tid)}",
                )
            )
        builder.row(
            CallbackButton(
                text=ClosedTasksTexts.MAIN_MENU_TEXT,
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()

    @staticmethod
    def create_cancel_confirm_keyboard(pyrus_task_id: int):
        builder = InlineKeyboardBuilder()
        tid = int(pyrus_task_id)
        builder.row(
            CallbackButton(
                text="✅ Подтвердить",
                payload=f"confirm_cancel_task:{tid}",
            ),
            CallbackButton(text="❌ Отмена", payload="cancel_task_abort"),
        )
        builder.row(
            CallbackButton(
                text=ClosedTasksTexts.MAIN_MENU_TEXT,
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()


class RatingKeyboards:
    """Оценка инженера 1–5 после закрытия заявки."""

    @staticmethod
    def create_engineer_rating_keyboard(pyrus_task_id: int) -> object:
        builder = InlineKeyboardBuilder()
        tid = int(pyrus_task_id)
        builder.row(
            *[CallbackButton(text=str(n), payload=f"eng_rating:{tid}:{n}") for n in range(1, 6)]
        )
        return builder.as_markup()


class CreateTaskKeyboards:

    @staticmethod
    async def build_themes_task_keyboard(items):
        builder = InlineKeyboardBuilder()
        emoji = "💻"
        row_buttons: list[CallbackButton] = []

        for item in items:
            item_id = item.get("item_id")
            if item_id is None:
                continue
            values = item.get("values") or []
            if not values:
                continue
            value = str(values[0])
            row_buttons.append(
                CallbackButton(
                    text=f"{emoji} {value}",
                    payload=f"theme_sel:{item_id}",
                )
            )
            if len(row_buttons) == 2:
                builder.row(*row_buttons)
                row_buttons = []

        if row_buttons:
            builder.row(*row_buttons)

        builder.row(
            CallbackButton(
                text="↩️ Вернуться в главное меню",
                payload="back_to_main_menu",
            )
        )
        return builder.as_markup()
