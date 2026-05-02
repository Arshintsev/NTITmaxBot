from pyrus import client
from pyrus.models.requests import CreateTaskRequest

# 1. Подключение к API
pyrus_client = client.PyrusAPI(
    login='arshintsev@mail.ru',
    security_key='~-OZfslTPgz-6IWcRPiaGcgNbOwhAl1B54s0gUbAuCqm3tx-hwQcZCsmxODMMxTtfzLsHNerleOKapAA32pxrkXUvm8Cv8RG'
)


def find_user_by_fullname(fullname: str) -> int | None:
    """
    Синхронно ищет пользователя по ФИО и возвращает ID задачи-пользователя
    """
    try:
        from pyrus.models.requests import FormRegisterRequest

        USERS_FORM_ID = 2304966
        request = FormRegisterRequest(include_archived=False)
        response = pyrus_client.get_registry(USERS_FORM_ID, request)

        if not response or not response.tasks:
            print("❌ Пользователи не найдены")
            return None

        # ID поля ФИО в форме пользователей (узнать через show_users_form_fields)
        FULLNAME_FIELD_ID = 32  # Уточните этот ID, запустив диагностику!

        for task in response.tasks:
            for field in task.fields:
                # Поиск по ID поля (быстрее и надежнее)
                if field.id == FULLNAME_FIELD_ID and field.value == fullname:
                    print(f"✅ Найден пользователь: {fullname} (ID задачи: {task.id})")
                    return task.id

                # Fallback: поиск по названию
                if field.name == "ФИО" and field.value == fullname:
                    print(f"✅ Найден пользователь: {fullname} (ID задачи: {task.id})")
                    return task.id

        print(f"❌ Пользователь с ФИО '{fullname}' не найден")
        return None

    except Exception as e:
        print(f"❌ Ошибка при поиске пользователя: {e}")
        return None





# Использование
user_id = find_user_by_fullname("Аршинцев Андрей Александрович")
if user_id:
    print(f"🔗 ID пользователя: {user_id}")
    print(f"📎 Ссылка: https://pyrus.com/task/{user_id}")