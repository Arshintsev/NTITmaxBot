import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from maxapi import Bot, Dispatcher
from maxapi.context import MemoryContext
from maxapi.enums.parse_mode import ParseMode
from app.handlers import register_all_handlers
from app.pyrus.instance import pyrus, client as pyrus_client
from app.data.instance import db
from app.ticket_closure_notify import closure_poll_loop, run_closure_poll_cycle
from app.pyrus_token_refresh import pyrus_token_refresh_loop

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('MAX_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен бота не найден!")

bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(storage=MemoryContext)

register_all_handlers(dp, pyrus)


async def main():
    # Явно инициализируем SQLite до старта polling.
    _ = db
    deleted_rows = db.delete_old_closed_tickets(days=60)
    if deleted_rows:
        logging.info("Удалено закрытых заявок старше 60 дней: %s", deleted_rows)

    sent = await run_closure_poll_cycle(bot, pyrus)
    if sent:
        logging.info("При старте отправлено уведомлений о закрытии: %s", sent)

    await pyrus_client.refresh_token_if_needed()

    poll_task = asyncio.create_task(closure_poll_loop(bot, pyrus))
    token_task = asyncio.create_task(pyrus_token_refresh_loop(pyrus_client))
    try:
        await dp.start_polling(bot)
    finally:
        for task in (poll_task, token_task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await pyrus_client.close()


if __name__ == '__main__':
    asyncio.run(main())