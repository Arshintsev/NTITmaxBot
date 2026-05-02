import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PYRUS_BASE_URL = os.getenv("PYRUS_BASE_URL")

    PYRUS_LOGIN = os.getenv("PYRUS_LOGIN")
    PYRUS_SECURITY_KEY = os.getenv("PYRUS_SECURITY_KEY")
    PYRUS_PERSON_ID = os.getenv("PYRUS_PERSON_ID")
    PYRUS_TASK_FORM_ID = int(os.getenv("PYRUS_TASK_FORM_ID", "2303165"))
    PYRUS_DEFAULT_PARTICIPANT_ID = os.getenv("PYRUS_DEFAULT_PARTICIPANT_ID")
    PYRUS_DEFAULT_PRIORITY_ITEM_ID = int(os.getenv("PYRUS_DEFAULT_PRIORITY_ITEM_ID", "168194724"))
    BOT_DB_PATH = os.getenv("BOT_DB_PATH", "data/bot.db")


settings = Settings()