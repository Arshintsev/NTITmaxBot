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
    # ID поля «Прикрепленные файлы» (тип file) на форме заявки.
    PYRUS_TASK_FILES_FIELD_ID = int(os.getenv("PYRUS_TASK_FILES_FIELD_ID", "35"))
    # Справочник тем обращений (как в рабочем боте: GET /catalogs/267947).
    PYRUS_THEMES_CATALOG_ID = int(os.getenv("PYRUS_THEMES_CATALOG_ID", "267947"))
    BOT_DB_PATH = os.getenv("BOT_DB_PATH", "data/bot.db")
    COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "30"))
    # Интервал проверки закрытых заявок в Pyrus и уведомления в MAX (секунды).
    CLOSURE_POLL_INTERVAL_SECONDS = int(os.getenv("CLOSURE_POLL_INTERVAL_SECONDS", "90"))
    # Окно показа «недавно закрытых» заявок в меню (часы).
    RECENTLY_CLOSED_HOURS = int(os.getenv("RECENTLY_CLOSED_HOURS", "1"))
    # Поля формы «Обращение клиента» для оценки после закрытия.
    PYRUS_TASK_RATING_FIELD_ID = int(os.getenv("PYRUS_TASK_RATING_FIELD_ID", "15"))
    PYRUS_TASK_RATING_DATE_FIELD_ID = int(
        os.getenv("PYRUS_TASK_RATING_DATE_FIELD_ID", "17")
    )


settings = Settings()