import asyncio
import logging
from typing import Any, Dict

import httpx

from app.config import settings
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
        fields: list[dict[str, Any]] = [
            {"id": 1, "value": data.get("theme_name") or "Без темы"},
            {"id": 2, "value": data.get("problem") or "Описание не указано"},
            {"id": 44, "value": data.get("pc_name") or "Не указан"},
            {"id": 118, "value": str(data.get("user_id", ""))},
            {"id": 6, "value": "".join(ch for ch in str(data.get("phone", "")) if ch.isdigit())},
            {"id": 36, "value": {"item_id": settings.PYRUS_DEFAULT_PRIORITY_ITEM_ID}},
        ]

        contractor_id = data.get("contractor_id")
        if contractor_id:
            fields.append({"id": 40, "value": {"task_id": int(contractor_id)}})

        client_task_id = data.get("client_task_id")
        if client_task_id:
            fields.append({"id": 39, "value": {"task_id": int(client_task_id)}})

        # Не отправляем catalog-поле "Тип заявки" из кнопок бота,
        # потому что значения theme_id в боте (1..N) не равны item_id каталога Pyrus.
        # Тема уже сохраняется в текстовом поле.

        payload: dict[str, Any] = {
            "text": f"Заявка от {data.get('name') or 'пользователя'}",
            "form_id": settings.PYRUS_TASK_FORM_ID,
            "fields": fields,
        }

        if settings.PYRUS_DEFAULT_PARTICIPANT_ID and settings.PYRUS_DEFAULT_PARTICIPANT_ID.isdigit():
            payload["participants"] = [int(settings.PYRUS_DEFAULT_PARTICIPANT_ID)]

        result = await self._request("POST", url, json=payload)

        task_id = result.get("task", {}).get("id")

        if not task_id:
            raise PyrusAPIError("No task_id returned")

        logger.info(f"[PYRUS] created task #{task_id}")

        return task_id

    async def close(self):
        await self._client.aclose()