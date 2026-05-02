import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

from maxapi import Bot, Dispatcher
from maxapi.context import MemoryContext
from app.handlers import register_all_handlers
from app.pyrus.instance import pyrus

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('MAX_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен бота не найден!")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryContext)

register_all_handlers(dp)


async def debug_pyrus_startup():
    task_id = 351833568
    await pyrus.debug_print_task(task_id)


async def main():
    try:
        await debug_pyrus_startup()
    except Exception as e:
        print(f"❌ Pyrus test failed: {e}")

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())