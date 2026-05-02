from pyrus import client
from pyrus.models.requests import CreateTaskRequest

# 1. Подключение к API
pyrus_client = client.PyrusAPI(
    login='arshintsev@mail.ru',
    security_key='~-OZfslTPgz-6IWcRPiaGcgNbOwhAl1B54s0gUbAuCqm3tx-hwQcZCsmxODMMxTtfzLsHNerleOKapAA32pxrkXUvm8Cv8RG'
)

# Формируем поля для задачи с указанием формы
request = CreateTaskRequest(
    text="Заявка от пользователя",
    participants=[1291379],  # ID ответственного
    form_id=2303165,  # ← ВАЖНО: ID вашей формы из лога!
    fields=[
        # Текстовые поля
        {'id': 1, 'value': 'ТЕСТ'},  # Проблема
        {'id': 2, 'value': 'ТЕСТ'},  # Описание
        {'id': 44, 'value': 'PC-001'},  # Имя ПК
        {'id': 118, 'value': 'TEST'}, #MAX
        {'id': 39, 'value': {"task_id": 351832735} }, #Пользователь
        {'id': 40, 'value': {'task_id': 285483103}},  # Контрагент (form_link)

        # Телефон
        {'id': 6, 'value': '79650550056'},  # Телефон

        # Каталоги
        {'id': 11, 'value': {'item_id': 168117889}},  # Тип заявки
        {'id': 36, 'value': {'item_id': 168194724}},  # Приоритет
    ]
)

# Отправка запроса
response = pyrus_client.create_task(request)
print(f"✅ Задача создана в форме! ID: {response.task.id}")