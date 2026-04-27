import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PYRUS_BASE_URL = os.getenv("PYRUS_BASE_URL")

    PYRUS_LOGIN = os.getenv("PYRUS_LOGIN")
    PYRUS_SECURITY_KEY = os.getenv("PYRUS_SECURITY_KEY")
    PYRUS_PERSON_ID = os.getenv("PYRUS_PERSON_ID")


settings = Settings()