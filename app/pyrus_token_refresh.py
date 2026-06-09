"""Фоновое обновление токена Pyrus до истечения срока жизни."""

import asyncio
import logging

from app.config import settings
from app.pyrus.client import PyrusClient

logger = logging.getLogger(__name__)


async def pyrus_token_refresh_loop(client: PyrusClient) -> None:
    interval = settings.PYRUS_TOKEN_REFRESH_INTERVAL_SECONDS
    if interval <= 0:
        return

    logger.info("Фоновое обновление токена Pyrus каждые %s с", interval)
    while True:
        try:
            await asyncio.sleep(interval)
            await client.refresh_token_if_needed()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Не удалось обновить токен Pyrus")
