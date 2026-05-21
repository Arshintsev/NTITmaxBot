import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from maxapi import Bot, Dispatcher
from maxapi.context import MemoryContext
from maxapi.enums.parse_mode import ParseMode
from app.handlers import register_all_handlers
from app.pyrus.instance import pyrus
from app.data.instance import db
from app.ticket_closure_notify import closure_poll_loop, run_closure_poll_cycle

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

    poll_task = asyncio.create_task(closure_poll_loop(bot, pyrus))
    try:
        await dp.start_polling(bot)
    finally:
        poll_task.cancel()
        try:
            await poll_task
        except asyncio.CancelledError:
            pass


if __name__ == '__main__':
    asyncio.run(main())