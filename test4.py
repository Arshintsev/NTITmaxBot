import pyrus
from pyrus import client
from pyrus.models.requests import FormRegisterRequest
from pyrus.models.entities import EqualsFilter

# 1. Подключение к API
pyrus_client = client.PyrusAPI(
    login='arshintsev@mail.ru',
    security_key='~-OZfslTPgz-6IWcRPiaGcgNbOwhAl1B54s0gUbAuCqm3tx-hwQcZCsmxODMMxTtfzLsHNerleOKapAA32pxrkXUvm8Cv8RG'
)

# ID формы "Пользователи"
USERS_FORM_ID = 2303165

# Получаем все формы
forms_response = pyrus_client.get_forms()

# Ищем нужную форму
for form in forms_response.forms:
    if form.id == USERS_FORM_ID:
        print(f"\n📋 ФОРМА: {form.name} (ID: {form.id})")
        print("=" * 60)

        for field in form.fields:
            print(f"  ID: {field.id} | Название: '{field.name}' | Тип: '{field.type}'")

            # Для полей-каталогов выводим catalog_id
            if field.type == 'catalog' and hasattr(field, 'catalog_id'):
                print(f"      Catalog ID: {field.catalog_id}")

        break