import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from maxapi import Bot, Dispatcher
from maxapi.context import MemoryContext
from app.handlers import register_all_handlers
from app.pyrus.instance import pyrus
from app.data.instance import db

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('MAX_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен бота не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryContext)

register_all_handlers(dp, pyrus)


async def main():
    # Явно инициализируем SQLite до старта polling.
    _ = db
    deleted_rows = db.delete_old_closed_tickets(days=60)
    if deleted_rows:
        logging.info("Удалено закрытых заявок старше 60 дней: %s", deleted_rows)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())