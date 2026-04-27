from typing import Dict, Any, List, Optional
from .models import PyrusTask, PyrusComment


# =========================
# FIELD HELPERS
# =========================

def _get_field(fields: list[dict], name: str):
    """
    Ищет поле по name или code
    """
    for f in fields:
        if f.get("name") == name or f.get("code") == name:
            return f.get("value")
    return None


def _get_choice_name(value: Any) -> Any:
    """
    Достаёт читаемое значение из multiple_choice
    """
    if isinstance(value, dict):
        names = value.get("choice_names") or []
        return names[0] if names else None
    return value


# =========================
# COMMENTS MAPPING
# =========================
def _map_comments(comments: List[dict]) -> List[PyrusComment]:
    result = []

    for c in comments or []:
        author = c.get("author", {})

        author_name = " ".join(
            filter(None, [
                author.get("first_name", ""),
                author.get("last_name", "")
            ])
        ).strip() or "Unknown"

        text_parts = []

        # 1. основной текст комментария
        if c.get("text"):
            text_parts.append(c["text"])

        # 2. field_updates (только осмысленные поля)
        for u in c.get("field_updates", []):
            u_type = u.get("type")
            val = u.get("value")

            if u_type in ("text", "note") and isinstance(val, str):
                if val.strip():
                    text_parts.append(val.strip())

        # ❗ убираем пустые комментарии
        if not text_parts:
            continue

        result.append(
            PyrusComment(
                id=c.get("id"),
                author_name=author_name,
                text=" | ".join(text_parts),
                created_at=c.get("create_date"),
            )
        )

    return result


# =========================
# TASK MAPPING
# =========================

def map_task(data: Dict[str, Any]) -> PyrusTask:
    task = data.get("task", {})
    fields = task.get("fields", [])

    return PyrusTask(
        id=task.get("id"),
        title=task.get("text"),

        # основные поля
        inn=_get_field(fields, "ИНН"),
        name=_get_field(fields, "Имя отправителя (из письма)")
             or _get_field(fields, "Контакт"),
        phone=_get_field(fields, "Телефон"),
        pc_name=_get_field(fields, "Имя ПК"),
        problem=_get_field(fields, "Описание"),

        # важное: нормализуем статус
        status=_get_choice_name(_get_field(fields, "Статус")),

        # комментарии
        comments=_map_comments(task.get("comments", [])),
    )