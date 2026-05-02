import pyrus
from pyrus import client
from pyrus.models.requests import FormRegisterRequest
from pyrus.models.entities import EqualsFilter

# 1. Подключение к API
pyrus_client = client.PyrusAPI(
    login='arshintsev@mail.ru',
    security_key='~-OZfslTPgz-6IWcRPiaGcgNbOwhAl1B54s0gUbAuCqm3tx-hwQcZCsmxODMMxTtfzLsHNerleOKapAA32pxrkXUvm8Cv8RG'
)

# 2. Получаем все формы
forms_response = pyrus_client.get_forms()
forms = forms_response.forms

# Запрос всех задач формы с фильтром по ID MAX
request = FormRegisterRequest(
    include_archived=False,
    filters=[
        EqualsFilter(118, "12345")  # field_id=118, значение ID MAX = "12345"
    ]
)

# Получаем список задач
form_register_response = pyrus_client.get_registry(2303165, request)
tasks = form_register_response.tasks

print(f"Найдено задач с ID MAX = 12345: {len(tasks)}")
for task in tasks:
    print(f"  - Задача {task.id}: {task.text}")