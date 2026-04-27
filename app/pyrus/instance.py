from app.config import settings
from app.pyrus.client import PyrusClient

pyrus = PyrusClient(
    login=settings.PYRUS_LOGIN,
    security_key=settings.PYRUS_SECURITY_KEY,
    person_id=settings.PYRUS_PERSON_ID,
)