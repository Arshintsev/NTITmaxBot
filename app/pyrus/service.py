import logging
import re
from datetime import date
from typing import Any, Dict, Optional

from app.config import settings

from .client import PyrusClient
from .mapper import map_task
from .models import PyrusTask

logger = logging.getLogger("pyrus")

_RATING_CHOICE_MAP_CACHE: dict[int, int] | None = None

# Справочник кнопок «Тема обращения» (не путать с полем «Тип заявки» id=11 на форме).
THEMES_CATALOG_DEFAULT_ID = 267947


class PyrusService:
    CONTRACTORS_FORM_ID = 2306222
    CONTRACTOR_INN_FIELD_ID = 5
    CONTRACTOR_NAME_FIELD_ID = 10
    CLIENTS_FORM_ID = 2304966
    CLIENT_FIO_FIELD_ID = 5
    CLIENT_CONTRACTOR_FIELD_ID = 10
    CLIENT_PHONE_FIELD_ID = 6
    CLIENT_MAX_ID_FIELD_ID = 15
    CLIENT_USER_ID_FIELD_ID = 14

    def __init__(self, client: PyrusClient):
        self.client = client

    async def get_task(self, task_id: int) -> PyrusTask:
        raw = await self.client._request(
            "GET",
            f"{self.client.base_url}/tasks/{task_id}",
        )
        return map_task(raw)

    async def get_task_safe(self, task_id: int) -> Optional[PyrusTask]:
        """GET задачи без исключения (403 и др. → None)."""
        raw, status = await self.client.request_status(
            "GET",
            f"{self.client.base_url}/tasks/{int(task_id)}",
        )
        if raw is None:
            if status == 403:
                logger.info("[PYRUS] Нет доступа к задаче %s (пропуск синхронизации)", task_id)
            elif status:
                logger.warning("[PYRUS] GET task %s -> HTTP %s", task_id, status)
            return None
        return map_task(raw)

    async def get_task_http_status(self, task_id: int) -> int:
        _, status = await self.client.request_status(
            "GET",
            f"{self.client.base_url}/tasks/{int(task_id)}",
        )
        return status

    async def create_task(self, data: dict):
        task_id = await self.client.create_ticket(data)

        await self.submit_task_comment(
            task_id=task_id,
            text=data.get("problem") or data.get("theme_name") or "Сообщение из MAX",
            attachments=data.get("attachments"),
            max_user_id=int(data.get("user_id", 0)),
        )

        return task_id

    @staticmethod
    def _rating_from_choice_label(label: str) -> int | None:
        """Сопоставляет подпись варианта поля «Оценка» с числом 1–5."""
        label = label.strip()
        if label.isdigit():
            n = int(label)
            if 1 <= n <= 5:
                return n
        m = re.match(r"^([1-5])\b", label)
        if m:
            return int(m.group(1))
        return None

    async def _load_rating_choice_map(self) -> dict[int, int]:
        """Рейтинг 1–5 → choice_id поля «Оценка» (multiple_choice)."""
        global _RATING_CHOICE_MAP_CACHE
        if _RATING_CHOICE_MAP_CACHE is not None:
            return _RATING_CHOICE_MAP_CACHE

        rating_field_id = settings.PYRUS_TASK_RATING_FIELD_ID
        raw = await self.client.request_json_optional(
            "GET",
            f"{self.client.base_url}/forms/{settings.PYRUS_TASK_FORM_ID}",
        )
        mapping: dict[int, int] = {}
        if raw:
            for field in raw.get("fields") or []:
                if not isinstance(field, dict):
                    continue
                if int(field.get("id") or 0) != rating_field_id:
                    continue
                options = (field.get("info") or {}).get("options") or []
                for opt in options:
                    if not isinstance(opt, dict) or opt.get("deleted"):
                        continue
                    cid = opt.get("choice_id")
                    if cid is None:
                        continue
                    label = str(opt.get("choice_value") or "")
                    stars = self._rating_from_choice_label(label)
                    if stars is not None:
                        mapping[stars] = int(cid)
                if len(mapping) < 5 and len(options) >= 5:
                    ordered = sorted(
                        (
                            int(o["choice_id"])
                            for o in options
                            if isinstance(o, dict)
                            and o.get("choice_id") is not None
                            and not o.get("deleted")
                        ),
                    )
                    if len(ordered) >= 5:
                        for stars, cid in enumerate(ordered[:5], start=1):
                            mapping.setdefault(stars, cid)
                break

        _RATING_CHOICE_MAP_CACHE = mapping
        if mapping:
            logger.info("Варианты оценки на форме: %s", mapping)
        else:
            logger.warning(
                "Не удалось загрузить варианты поля «Оценка» (id=%s)",
                rating_field_id,
            )
        return mapping

    async def submit_user_rating(
        self, task_id: int, rating: int, max_user_id: int
    ) -> bool:
        """
        Заполняет поля «Оценка» и «Дата оценки» без текста в ленте.
        skip_auto_reopen — не переоткрывать закрытую задачу.
        """
        if not 1 <= rating <= 5:
            return False

        choice_map = await self._load_rating_choice_map()
        choice_id = choice_map.get(rating)
        if choice_id is None:
            logger.warning(
                "Нет choice_id для оценки %s (задача %s)", rating, task_id
            )
            return False

        field_updates: list[dict[str, Any]] = [
            {
                "id": settings.PYRUS_TASK_RATING_FIELD_ID,
                "value": {"choice_ids": [choice_id]},
            },
            {
                "id": settings.PYRUS_TASK_RATING_DATE_FIELD_ID,
                "value": date.today().isoformat(),
            },
        ]

        try:
            await self.client.add_task_comment(
                task_id,
                field_updates=field_updates,
                skip_auto_reopen=True,
            )
            return True
        except Exception as e:
            logger.warning(
                "Не удалось записать оценку в Pyrus для задачи %s: %s",
                task_id,
                e,
            )
            return False

    MAX_MESSENGER_CHANNEL = {"type": "max_messenger"}

    async def submit_task_comment(
        self,
        task_id: int,
        *,
        text: str,
        attachments: list[dict[str, Any]] | None = None,
        max_user_id: int,
    ) -> bool:
        """Комментарий из MAX в Pyrus через канал max_messenger."""
        prepared: list[dict[str, Any]] = []
        if attachments:
            prepared = await self.client._prepare_attachments_for_pyrus(attachments)

        body = (text or "").strip()
        if not body and prepared:
            body = "Вложение"

        pyrus_attachments = [
            {"guid": item["guid"], "name": item.get("name") or "Вложение"}
            for item in prepared
            if item.get("guid")
        ]

        if not body and not pyrus_attachments:
            return False

        try:
            await self.client.add_task_comment(
                task_id,
                text=body or None,
                attachments=pyrus_attachments or None,
                channel=self.MAX_MESSENGER_CHANNEL,
                skip_auto_reopen=False,
            )
            return True
        except Exception as e:
            logger.warning(
                "Не удалось отправить комментарий в Pyrus (задача %s, MAX %s): %s",
                task_id,
                max_user_id,
                e,
            )
            return False

    async def close_task_by_user(self, task_id: int, max_user_id: int) -> bool:
        """Закрывает заявку от имени пользователя (action=finished)."""
        from app.text import TaskActionsMessages

        text = (
            f"{TaskActionsMessages.USER_CLOSE_TASK_TEXT}\n"
            f"(MAX, пользователь {max_user_id})"
        )
        try:
            await self.client.add_task_comment(
                task_id,
                text=text,
                action="finished",
                skip_auto_reopen=True,
            )
            return True
        except Exception as e:
            logger.warning(
                "Не удалось закрыть задачу %s в Pyrus: %s", task_id, e
            )
            return False

    async def reopen_task_by_user(self, task_id: int, max_user_id: int) -> bool:
        from app.text import ClosedTasksTexts

        text = (
            f"{ClosedTasksTexts.USER_OPEN_TASK}\n"
            f"(MAX, пользователь {max_user_id})"
        )
        try:
            await self.client.add_task_comment(
                task_id,
                text=text,
                action="reopened",
                skip_auto_reopen=False,
            )
            return True
        except Exception as e:
            logger.warning(
                "Не удалось переоткрыть задачу %s в Pyrus: %s", task_id, e
            )
            return False

    async def get_items(self) -> list[dict[str, Any]]:
        """
        Элементы справочника тем (GET /catalogs/{PYRUS_THEMES_CATALOG_ID}).
        Тот же каталог, что в рабочем Telegram-боте: /catalogs/267947.
        """
        return await self.get_themes()

    async def get_themes(self) -> list[dict[str, Any]]:
        """Темы обращения из справочника Pyrus — формат как у get_items() в старом боте."""
        stub = [
            {"item_id": "1", "values": ["Проблема с интернетом"]},
            {"item_id": "2", "values": ["Не работает ПК"]},
            {"item_id": "3", "values": ["Ошибка в программе"]},
            {"item_id": "4", "values": ["Доступы / аккаунты"]},
        ]

        catalog_id = settings.PYRUS_THEMES_CATALOG_ID
        if not catalog_id or catalog_id <= 0:
            catalog_id = THEMES_CATALOG_DEFAULT_ID

        raw = await self.client.request_json_optional(
            "GET",
            f"{self.client.base_url}/catalogs/{catalog_id}",
        )
        if not raw:
            logger.warning(
                "Не удалось загрузить /catalogs/%s — заглушка. Проверьте PYRUS_THEMES_CATALOG_ID и права в Pyrus",
                catalog_id,
            )
            return stub

        rows = raw.get("items", [])
        if not isinstance(rows, list) or not rows:
            logger.warning("Справочник %s пуст — заглушка", catalog_id)
            return stub

        result: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("deleted") or row.get("is_deleted"):
                continue
            vals = row.get("values") or []
            if not vals or not str(vals[0]).strip():
                continue
            # Оставляем структуру ответа Pyrus: item_id + values (как в get_items).
            result.append(
                {
                    "item_id": row.get("item_id"),
                    "values": vals,
                }
            )

        if not result:
            return stub

        logger.info("Загружено тем из /catalogs/%s: %s", catalog_id, len(result))
        return result

    async def get_contractor_info(self, inn: str) -> Optional[Dict[str, Any]]:
        """Возвращает данные контрагента по ИНН."""
        try:
            url = f"{self.client.base_url}/forms/{self.CONTRACTORS_FORM_ID}/register"
            normalized_inn = "".join(ch for ch in inn if ch.isdigit())
            filter_key = f"fld{self.CONTRACTOR_INN_FIELD_ID}"

            # Один простой запрос в реестр формы по ИНН.
            response = await self.client._request(
                "GET",
                url,
                params={
                    filter_key: f"eq.{normalized_inn}",
                    "item_count": 50,
                    "sort": "id",
                    "include_archived": "y",
                },
            )

            tasks = response.get("tasks", []) if isinstance(response, dict) else []
            if not tasks:
                return None

            task = self._find_task_by_inn(tasks, normalized_inn)
            if not task:
                return None

            company_name = self._extract_field_value(
                task.get("fields", []),
                self.CONTRACTOR_NAME_FIELD_ID,
            )
            return {
                "id": task.get("id"),
                "name": company_name,
                "inn": normalized_inn,
            }

        except Exception:
            return None

    async def get_client_info(self, fio: str, contractor_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """
        Ищет клиента по ФИО в форме "Клиенты" с приоритетом совпадения контрагента.
        """
        try:
            url = f"{self.client.base_url}/forms/{self.CLIENTS_FORM_ID}/register"
            normalized_fio = " ".join((fio or "").strip().split())
            if not normalized_fio:
                return None

            response = await self.client._request(
                "GET",
                url,
                params={
                    f"fld{self.CLIENT_FIO_FIELD_ID}": normalized_fio,
                    "item_count": 200,
                    "sort": "id",
                    "include_archived": "y",
                },
            )

            tasks = response.get("tasks", []) if isinstance(response, dict) else []
            if not tasks:
                return None

            target_last_name = normalized_fio.split()[0].lower()
            for task in tasks:
                task_fio = self._extract_field_value(task.get("fields", []), self.CLIENT_FIO_FIELD_ID) or ""
                task_last_name = task_fio.split()[0].lower() if task_fio.split() else ""
                if task_last_name != target_last_name:
                    continue

                if contractor_id is not None:
                    task_contractor_id = self._extract_task_link_id(
                        task.get("fields", []),
                        self.CLIENT_CONTRACTOR_FIELD_ID,
                    )
                    if task_contractor_id != int(contractor_id):
                        continue

                return {
                    "id": task.get("id"),
                    "fio": task_fio,
                    "phone": self._extract_field_value(task.get("fields", []), self.CLIENT_PHONE_FIELD_ID),
                }
            return None
        except Exception:
            return None

    async def ensure_client_for_ticket(self, data: dict[str, Any]) -> Optional[int]:
        """
        Возвращает ID клиента из формы "Клиенты".
        Если клиент не найден, создаёт его и возвращает новый ID.
        """
        existing_client_id = data.get("client_task_id")
        if existing_client_id:
            return int(existing_client_id)

        fio = (data.get("name") or "").strip()
        contractor_id = data.get("contractor_id")
        phone = data.get("phone")
        max_user_id = data.get("user_id")

        found_client = await self.get_client_info(fio=fio, contractor_id=contractor_id)
        if found_client and found_client.get("id"):
            return int(found_client["id"])

        created_client_id = await self._create_client(
            fio=fio,
            contractor_id=contractor_id,
            phone=phone,
            max_user_id=max_user_id,
        )
        return created_client_id

    @staticmethod
    def _extract_field_value(fields: list[dict[str, Any]], field_id: int) -> Optional[str]:
        for field in fields:
            if field.get("id") != field_id:
                continue
            value = field.get("value")
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                choice_names = value.get("choice_names") or []
                if choice_names:
                    return str(choice_names[0])
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _extract_task_link_id(fields: list[dict[str, Any]], field_id: int) -> Optional[int]:
        for field in fields:
            if field.get("id") != field_id:
                continue
            value = field.get("value")
            if isinstance(value, dict) and value.get("task_id"):
                return int(value["task_id"])
        return None

    def _find_task_by_inn(self, tasks: list[dict[str, Any]], inn: str) -> Optional[dict[str, Any]]:
        """Ищет задачу, у которой поле ИНН точно совпадает с введенным ИНН."""
        for task in tasks:
            task_inn = self._extract_field_value(task.get("fields", []), self.CONTRACTOR_INN_FIELD_ID)
            normalized_task_inn = "".join(ch for ch in str(task_inn or "") if ch.isdigit())
            if normalized_task_inn == inn:
                return task
        return None

    async def _create_client(
        self,
        *,
        fio: str,
        contractor_id: Optional[int],
        phone: Optional[str],
        max_user_id: Optional[int],
    ) -> Optional[int]:
        """
        Создаёт клиента в форме "Клиенты" и привязывает к контрагенту.
        """
        if not fio:
            return None

        fields: list[dict[str, Any]] = [
            {"id": self.CLIENT_FIO_FIELD_ID, "value": fio},
        ]

        if contractor_id:
            fields.append(
                {
                    "id": self.CLIENT_CONTRACTOR_FIELD_ID,
                    "value": {"task_id": int(contractor_id)},
                }
            )

        if phone:
            normalized_phone = "".join(ch for ch in str(phone) if ch.isdigit())
            if normalized_phone:
                fields.append({"id": self.CLIENT_PHONE_FIELD_ID, "value": normalized_phone})

        if max_user_id is not None:
            fields.append({"id": self.CLIENT_MAX_ID_FIELD_ID, "value": str(max_user_id)})
            fields.append({"id": self.CLIENT_USER_ID_FIELD_ID, "value": str(max_user_id)})

        response = await self.client._request(
            "POST",
            f"{self.client.base_url}/tasks",
            json={
                "text": f"Клиент {fio}",
                "form_id": self.CLIENTS_FORM_ID,
                "fields": fields,
            },
        )

        task = response.get("task", {}) if isinstance(response, dict) else {}
        task_id = task.get("id")
        return int(task_id) if task_id else None