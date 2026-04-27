import asyncio
import logging
from typing import Any, Dict

import httpx

from .exceptions import PyrusNetworkError, PyrusAPIError, PyrusAuthError
from .error_mapper import  map_http_error
from .mapper import map_task

logger = logging.getLogger("pyrus")

ACCOUNTS_API = "https://accounts.pyrus.com/api/v4"


class PyrusClient:
    def __init__(
        self,
        login: str,
        security_key: str,
        person_id: str,
        base_url: str = "https://api.pyrus.com/v4",
        timeout: int = 10,
    ):
        # защита от твоей прошлой ошибки (NoneType.rstrip)
        if not base_url:
            raise ValueError("base_url is required")
        if not login or not security_key or not person_id:
            raise ValueError("Pyrus credentials are not fully set")

        self.base_url = base_url.rstrip("/")
        self.login = login
        self.security_key = security_key
        self.person_id = person_id
        self.timeout = timeout

        self._token: str | None = None

        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    # =========================
    # AUTH (КАК В РАБОЧЕМ БОТЕ)
    # =========================

    async def _auth(self) -> str:
        logger.info("[PYRUS] auth request")

        response = await self._client.post(
            f"{ACCOUNTS_API}/auth",
            json={
                "login": self.login,
                "security_key": self.security_key,
                "person_id": self.person_id,
            },
        )

        if response.status_code >= 400:
            logger.error(f"[PYRUS] auth failed: {response.text}")
            raise PyrusAuthError("Auth failed")

        token = response.json().get("access_token")

        if not token:
            raise PyrusAuthError("No access token received")

        self._token = token
        return token

    async def _get_headers(self) -> dict:
        if not self._token:
            await self._auth()

        return {
            "Authorization": f"Bearer {self._token}",
        }

    # =========================
    # REQUEST WRAPPER (RETRY + LOGGING)
    # =========================

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        retries = 3
        last_error = None

        for attempt in range(retries):
            try:
                headers = kwargs.pop("headers", {})
                headers.update(await self._get_headers())

                logger.info(f"[PYRUS] {method} {url} attempt={attempt + 1}")

                response = await self._client.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs,
                )

                # если токен протух → переавторизация
                if response.status_code == 401:
                    logger.warning("[PYRUS] token expired, reauth")
                    self._token = None
                    await self._auth()
                    continue

                if response.status_code >= 400:
                    raise map_http_error(response.status_code, response.text)

                return response.json()

            except httpx.RequestError as e:
                logger.warning(f"[PYRUS] network error: {e}")
                last_error = PyrusNetworkError(str(e))
                await asyncio.sleep(0.5 * (attempt + 1))

            except Exception as e:
                logger.exception(f"[PYRUS] fatal error: {e}")
                raise

        raise last_error or PyrusNetworkError("Unknown network error")

    # =========================
    # DEBUG GET TASK
    # =========================

    async def debug_print_task(self, task_id: int):
        url = f"{self.base_url}/tasks/{task_id}"

        logger.info(f"[PYRUS DEBUG] GET {url}")

        raw = await self._request("GET", url)

        task = map_task(raw)

        print("\n" + "=" * 60)
        print(f"🔥 PYRUS TASK #{task.id}")
        print(f"📌 TITLE: {task.title}")
        print(f"📱 PHONE: {task.phone}")
        print(f"💻 PC: {task.pc_name}")
        print(f"❗ PROBLEM: {task.problem}")
        print(f"📊 STATUS: {task.status}")

        print("\n💬 COMMENTS:")
        for c in task.comments:
            print(f"- {c.author_name}: {c.text}")

        print("=" * 60 + "\n")

        return task

    # =========================
    # CREATE TICKET
    # =========================

    async def create_ticket(self, data: Dict[str, Any]) -> int:
        url = f"{self.base_url}/tasks"

        payload = {
            "subject": f"Заявка от {data.get('name')}",
            "fields": {
                "inn": data.get("inn"),
                "name": data.get("name"),
                "phone": data.get("phone"),
                "pc_name": data.get("pc_name"),
                "problem": data.get("problem"),
                "theme_id": data.get("theme_id"),
            },
        }

        result = await self._request("POST", url, json=payload)

        task_id = result.get("task", {}).get("id")

        if not task_id:
            raise PyrusAPIError("No task_id returned")

        logger.info(f"[PYRUS] created task #{task_id}")

        return task_id

    async def close(self):
        await self._client.aclose()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (ЗАГЛУШКИ) ==========
def get_user_active_tasks(user_id: int) -> list:
    """Получить активные задачи пользователя (заглушка)"""
    return [
        {'id': 1, 'title': 'Проблема с оплатой', 'status': 'active'},
        {'id': 2, 'title': 'Техническая поддержка', 'status': 'active'},
        {'id': 3, 'title': 'Вопрос по документации', 'status': 'active'},
    ]


def get_user_closed_tasks(user_id: int) -> list:
    """Получить закрытые задачи пользователя (заглушка)"""
    return [
        {'id': 100, 'title': 'Создание аккаунта', 'status': 'closed'},
        {'id': 101, 'title': 'Настройка бота', 'status': 'closed'},
    ]

def save_ticket(data: dict) -> int:
    """Сохранить заявку"""
    import random

    ticket_id = random.randint(1000, 9999)

    print(
        f"""
        ✅ Заявка #{ticket_id}
        user_id: {data.get('user_id')}
        inn: {data.get('inn')}
        name: {data.get('name')}
        phone: {data.get('phone')}
        pc_name: {data.get('pc_name')}
        problem: {data.get('problem')}
        """
    )

    return ticket_id


def save_comment(task_id: int, user_id: int, text: str) -> None:
    """Сохранить комментарий к задаче (заглушка)"""
    print(f"💬 Комментарий к задаче #{task_id} от {user_id}: {text}")


def cancel_task(task_id: int, user_id: int) -> None:
    """Отменить задачу (заглушка)"""
    print(f"❌ Задача #{task_id} отменена пользователем {user_id}")

def check_inn_in_db(inn_number: str) -> bool:
    """Проверка существования ИНН в базе CRM (тестовый стенд)"""
    valid_inns = {"1111111111", "7701010101", "7712345678"}
    return inn_number in valid_inns

import asyncio


async def get_themes_from_api():
    """
    Заглушка CRM/API.
    Потом тут будет реальный запрос в Pyrus / CRM / HTTP.
    """

    await asyncio.sleep(0.2)  # имитация сети

    return [
        {"item_id": "1", "values": ["Проблема с интернетом"]},
        {"item_id": "2", "values": ["Не работает ПК"]},
        {"item_id": "3", "values": ["Ошибка в программе"]},
        {"item_id": "4", "values": ["Доступы / аккаунты"]},
    ]