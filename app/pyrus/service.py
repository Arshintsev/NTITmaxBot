from typing import Any, Dict, Optional

from .client import PyrusClient
from .mapper import map_task


class PyrusService:
    CONTRACTORS_FORM_ID = 2306222
    CONTRACTOR_INN_FIELD_ID = 5
    CONTRACTOR_NAME_FIELD_ID = 10
    CLIENTS_FORM_ID = 2304966
    CLIENT_FIO_FIELD_ID = 5
    CLIENT_CONTRACTOR_FIELD_ID = 10
    CLIENT_PHONE_FIELD_ID = 6

    def __init__(self, client: PyrusClient):
        self.client = client

    async def get_task(self, task_id: int):
        raw = await self.client._request(
            "GET",
            f"{self.client.base_url}/tasks/{task_id}"
        )

        return map_task(raw)

    async def create_task(self, data: dict):
        return await self.client.create_ticket(data)

    async def get_themes(self) -> list[dict[str, Any]]:
        """
        Заглушка для тем обращения.
        Позже можно заменить на чтение из формы/справочника Pyrus.
        """
        return [
            {"item_id": "1", "values": ["Проблема с интернетом"]},
            {"item_id": "2", "values": ["Не работает ПК"]},
            {"item_id": "3", "values": ["Ошибка в программе"]},
            {"item_id": "4", "values": ["Доступы / аккаунты"]},
        ]

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