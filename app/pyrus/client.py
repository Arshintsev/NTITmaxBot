import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict
import re

import httpx

from app.config import settings
from .exceptions import PyrusNetworkError, PyrusAPIError, PyrusAuthError
from .error_mapper import  map_http_error
from .mapper import map_task

logger = logging.getLogger("pyrus")

ACCOUNTS_API = "https://accounts.pyrus.com/api/v4"

# Соответствие расширений и MIME для корректного отображения в Pyrus (не как «бинарный» файл).
_MIME_BY_EXT: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".zip": "application/zip",
    ".rar": "application/x-rar-compressed",
    ".7z": "application/x-7z-compressed",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
}


def _filename_from_content_disposition(header: str | None) -> str | None:
    if not header:
        return None
    # filename*=UTF-8''... или filename="..."
    m = re.search(r"filename\*=(?:UTF-8''|)([^;\r\n]+)", header, re.IGNORECASE)
    if m:
        from urllib.parse import unquote
        return unquote(m.group(1).strip().strip('"'))
    m = re.search(r'filename="([^"]+)"', header)
    if m:
        return m.group(1)
    m = re.search(r"filename=([^;\r\n]+)", header)
    if m:
        return m.group(1).strip().strip('"')
    return None


def _ext_and_mime_from_content_type(ct: str | None) -> tuple[str, str] | None:
    if not ct:
        return None
    ct_main = ct.split(";")[0].strip().lower()
    mapping = {
        "image/jpeg": (".jpg", "image/jpeg"),
        "image/jpg": (".jpg", "image/jpeg"),
        "image/png": (".png", "image/png"),
        "image/gif": (".gif", "image/gif"),
        "image/webp": (".webp", "image/webp"),
        "image/bmp": (".bmp", "image/bmp"),
        "image/tiff": (".tiff", "image/tiff"),
        "application/pdf": (".pdf", "application/pdf"),
        "text/plain": (".txt", "text/plain; charset=utf-8"),
    }
    return mapping.get(ct_main)


def _sniff_file_kind(content: bytes) -> tuple[str, str] | None:
    """Определяет расширение и MIME по сигнатуре файла."""
    if len(content) < 12:
        return None
    if content[:3] == b"\xff\xd8\xff":
        return (".jpg", "image/jpeg")
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return (".png", "image/png")
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return (".gif", "image/gif")
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return (".webp", "image/webp")
    if content[:4] == b"%PDF":
        return (".pdf", "application/pdf")
    if content[:2] == b"PK":
        head = content[: min(16000, len(content))]
        if b"[Content_Types].xml" in head and b"word/" in head:
            return (
                ".docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        if b"[Content_Types].xml" in head and b"xl/" in head:
            return (
                ".xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        return (".zip", "application/zip")
    return None


# Недопустимые в имени файла символы (кроссплатформенно).
_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_filename_stem(stem: str) -> str:
    """Оставляем кириллицу и латиницу, убираем только опасные символы."""
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", (stem or "").strip())
    return cleaned or "file"


def _finalize_upload_name_and_mime(
    content: bytes,
    filename_hint: str,
    content_type_header: str | None,
) -> tuple[str, str]:
    """
    Возвращает (имя файла с расширением, MIME для multipart).
    Если в имени уже есть известное расширение (.jpg, .png, .webp…) — как при отправке пользователем.
    Иначе — по Content-Type или сигнатуре файла.
    """
    hint_path = Path(filename_hint or "file")
    hint_stem = _safe_filename_stem(hint_path.stem)
    hint_ext = hint_path.suffix.lower()

    sniff = _sniff_file_kind(content)
    from_ct = _ext_and_mime_from_content_type(content_type_header)

    if hint_ext in _MIME_BY_EXT:
        mime = _MIME_BY_EXT[hint_ext]
        return f"{hint_stem}{hint_ext}", mime

    if from_ct:
        ext, mime = from_ct
        return f"{hint_stem}{ext}", mime

    if sniff:
        ext, mime = sniff
        return f"{hint_stem}{ext}", mime

    return f"{hint_stem}.bin", "application/octet-stream"


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
        self._token_expires_at: float = 0.0
        self._auth_lock = asyncio.Lock()

        self._client = httpx.AsyncClient(
            timeout=timeout,
        )

    # =========================
    # AUTH (КАК В РАБОЧЕМ БОТЕ)
    # =========================

    async def _auth(self) -> str:
        async with self._auth_lock:
            if self._token and time.monotonic() < self._token_expires_at:
                return self._token

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

            data = response.json()
            token = data.get("access_token")

            if not token:
                raise PyrusAuthError("No access token received")

            expires_in = int(data.get("expires_in") or 1800)
            refresh_margin = min(300, max(60, expires_in // 6))
            self._token = token
            self._token_expires_at = time.monotonic() + max(
                60, expires_in - refresh_margin
            )
            logger.info(
                "[PYRUS] token получен, обновление через ~%s с",
                int(self._token_expires_at - time.monotonic()),
            )
            return token

    async def refresh_token_if_needed(self) -> None:
        """Проактивное обновление до истечения срока жизни токена."""
        if not self._token or time.monotonic() >= self._token_expires_at:
            await self._auth()

    async def _get_headers(self) -> dict:
        await self.refresh_token_if_needed()
        return {
            "Authorization": f"Bearer {self._token}",
        }

    async def _reauth(self) -> None:
        self._token = None
        self._token_expires_at = 0.0
        await self._auth()

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

                if response.status_code == 401:
                    logger.warning("[PYRUS] HTTP 401, повторная авторизация")
                    await self._reauth()
                    if attempt < retries - 1:
                        continue
                    raise PyrusAuthError("Pyrus token expired")

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

    async def request_json_optional(self, method: str, url: str, **kwargs) -> Dict[str, Any] | None:
        """
        Запрос без исключения при 4xx/5xx — для справочников и прочих необязательных данных.
        """
        try:
            headers = kwargs.pop("headers", {})
            headers.update(await self._get_headers())
            response = await self._client.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                await self._reauth()
                headers.update(await self._get_headers())
                response = await self._client.request(method, url, headers=headers, **kwargs)
            if response.status_code >= 400:
                logger.warning(
                    "[PYRUS] %s %s -> HTTP %s: %s",
                    method,
                    url,
                    response.status_code,
                    response.text[:300],
                )
                return None
            return response.json()
        except httpx.RequestError as e:
            logger.warning("[PYRUS] %s %s network error: %s", method, url, e)
            return None

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

        # Сначала грузим файлы в Pyrus, затем прикладываем к полю формы «Прикрепленные файлы» (тип file).
        attachments = data.get("attachments", [])
        prepared_attachments: list[dict[str, Any]] = []
        if isinstance(attachments, list) and attachments:
            prepared_attachments = await self._prepare_attachments_for_pyrus(attachments)

        sender_name = (data.get("name") or "").strip() or "не указано"
        problem_text = (data.get("problem") or "").strip() or "Описание не указано"
        description_value = f"⚠️ ФИО отправителя: {sender_name}\n\n{problem_text}"

        fields: list[dict[str, Any]] = [
            {"id": 1, "value": data.get("theme_name") or "Без темы"},
            {"id": 2, "value": description_value},
            {"id": 44, "value": data.get("pc_name") or "Не указан"},
            {"id": 118, "value": str(data.get("user_id", ""))},
            {"id": 6, "value": "".join(ch for ch in str(data.get("phone", "")) if ch.isdigit())},
            {"id": 36, "value": {"item_id": settings.PYRUS_DEFAULT_PRIORITY_ITEM_ID}},
            {"id": 32, "value": str(data.get("user_id"))},

        ]

        contractor_id = data.get("contractor_id")
        if contractor_id:
            fields.append({"id": 40, "value": {"task_id": int(contractor_id)}})

        client_task_id = data.get("client_task_id")
        if client_task_id:
            fields.append({"id": 39, "value": {"task_id": int(client_task_id)}})

        # Поле «Тип заявки» (catalog 263603) не заполняем — только текстовая «Тема» в поле «Проблема» (id=1).

        if prepared_attachments:
            # Формат как у attachments в API Pyrus (см. справку по полю file).
            file_field_value: list[dict[str, Any]] = []
            for item in prepared_attachments:
                entry: dict[str, Any] = {"guid": item["guid"]}
                if item.get("name"):
                    entry["name"] = item["name"]
                file_field_value.append(entry)
            fields.append(
                {
                    "id": settings.PYRUS_TASK_FILES_FIELD_ID,
                    "value": file_field_value,
                }
            )

        theme_name = data.get("theme_name") or "Без темы"
        payload: dict[str, Any] = {
            "text": (
                f"Заявка от {data.get('name') or 'пользователя'}\n"
                f"Тема: {theme_name}"
            ),
            "form_id": settings.PYRUS_TASK_FORM_ID,
            "fields": fields,
            "channel": {
                "type": "max_messenger"
            }

        }

        if settings.PYRUS_DEFAULT_PARTICIPANT_ID and settings.PYRUS_DEFAULT_PARTICIPANT_ID.isdigit():
            payload["participants"] = [int(settings.PYRUS_DEFAULT_PARTICIPANT_ID)]

        result = await self._request("POST", url, json=payload)

        task_id = result.get("task", {}).get("id")

        if not task_id:
            raise PyrusAPIError("No task_id returned")

        logger.info(f"[PYRUS] created task #{task_id}")

        return task_id

    async def request_status(
        self, method: str, url: str, **kwargs
    ) -> tuple[Dict[str, Any] | None, int]:
        """Запрос без исключения: (json или None, HTTP-код)."""
        try:
            headers = kwargs.pop("headers", {})
            headers.update(await self._get_headers())
            response = await self._client.request(method, url, headers=headers, **kwargs)
            if response.status_code == 401:
                await self._reauth()
                headers.update(await self._get_headers())
                response = await self._client.request(method, url, headers=headers, **kwargs)
            if response.status_code >= 400:
                return None, response.status_code
            if not response.content:
                return {}, response.status_code
            return response.json(), response.status_code
        except httpx.RequestError as e:
            logger.warning("[PYRUS] %s %s network error: %s", method, url, e)
            return None, 0

    async def add_task_comment(
        self,
        task_id: int,
        text: str | None = None,
        *,
        field_updates: list[dict[str, Any]] | None = None,
        attachments: list[dict[str, Any]] | None = None,
        action: str | None = None,
        channel: dict[str, Any] | None = None,
        skip_auto_reopen: bool = True,
    ) -> None:
        """
        Комментарий к задаче. skip_auto_reopen=True — не переоткрывать закрытую задачу.
        channel — внешний канал (например {"type": "max_messenger"} для комментария из MAX).
        """
        if not text and not field_updates and not attachments and not action:
            raise ValueError(
                "add_task_comment: нужен text, field_updates, attachments или action"
            )
        url = f"{self.base_url}/tasks/{int(task_id)}/comments"
        payload: dict[str, Any] = {"skip_auto_reopen": skip_auto_reopen}
        if text:
            payload["text"] = text
        if field_updates:
            payload["field_updates"] = field_updates
        if attachments:
            payload["attachments"] = attachments
        if action:
            payload["action"] = action
        if channel:
            payload["channel"] = channel
        await self._request("POST", url, json=payload)

    async def _prepare_attachments_for_pyrus(self, attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Загружает файлы в Pyrus и возвращает список {guid, name} для поля типа file на форме.
        """
        prepared: list[dict[str, Any]] = []
        for item in attachments:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if not url:
                continue
            name = item.get("name") or "Вложение"

            result = await self._upload_file_from_url(url, name)
            if not result:
                continue
            guid, attach_name = result
            prepared.append({"guid": guid, "name": attach_name})
        logger.info("[PYRUS] Подготовлено вложений для отправки: %s из %s", len(prepared), len(attachments))
        return prepared

    async def _download_file_bytes(self, url: str) -> tuple[bytes, str | None, str | None] | None:
        """
        Скачивает файл по внешнему URL (MAX/oneme) отдельным клиентом — без смешивания с API Pyrus.
        Возвращает (content, content_type, content_disposition) или None.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; NTITmaxBot/1.0)",
            "Accept": "*/*",
        }
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=httpx.Timeout(60.0, connect=15.0),
                verify=True,
            ) as downloader:
                response = await downloader.get(url, headers=headers)
                if response.status_code >= 400 or not response.content:
                    logger.warning(
                        "[PYRUS] Скачивание вложения HTTP %s: %s",
                        response.status_code,
                        url,
                    )
                    return None
                return (
                    response.content,
                    response.headers.get("Content-Type"),
                    response.headers.get("Content-Disposition"),
                )
        except Exception as e:
            logger.warning("[PYRUS] Скачивание вложения не удалось (%s): %s", url, e)
            return None

    async def _upload_file_from_url(self, url: str, file_name: str) -> tuple[str, str] | None:
        """
        Скачивает файл по URL и загружает в Pyrus через /files/upload.
        Возвращает (guid, имя_для_отображения) или None при ошибке.
        """
        try:
            downloaded = await self._download_file_bytes(url)
            if not downloaded:
                return None
            file_content, content_type, content_disposition = downloaded
            if not file_content:
                return None

            cd_fn = _filename_from_content_disposition(content_disposition)
            hint = cd_fn or file_name

            safe_name, mime = _finalize_upload_name_and_mime(
                file_content,
                hint,
                content_type,
            )
            logger.debug("[PYRUS] Вложение: имя=%s MIME=%s размер=%s", safe_name, mime, len(file_content))

            headers = await self._get_headers()
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as upload_client:
                upload_response = await upload_client.post(
                    f"{self.base_url}/files/upload",
                    headers=headers,
                    files={safe_name: (safe_name, file_content, mime)},
                )
                if upload_response.status_code >= 400:
                    upload_response = await upload_client.post(
                        f"{self.base_url}/files/upload",
                        headers=headers,
                        files={"file": (safe_name, file_content, mime)},
                    )
                    if upload_response.status_code >= 400:
                        logger.warning("[PYRUS] upload файла не удался: %s", upload_response.text)
                        return None

            body = upload_response.json()
            guid = body.get("guid")
            if not guid:
                return None
            return (str(guid), safe_name)
        except Exception as e:
            logger.warning("[PYRUS] Ошибка загрузки вложения: %s", e)
            return None

    async def close(self):
        await self._client.aclose()