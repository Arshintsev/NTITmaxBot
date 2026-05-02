from app.config import settings
from app.pyrus.client import PyrusClient
from app.pyrus.service import PyrusService  # ← добавляем импорт

# Создаем клиент
client = PyrusClient(
    login=settings.PYRUS_LOGIN,
    security_key=settings.PYRUS_SECURITY_KEY,
    person_id=settings.PYRUS_PERSON_ID,
)

# Создаем сервис (обертку с бизнес-логикой)
pyrus = PyrusService(client)  # ← теперь pyrus — это сервис