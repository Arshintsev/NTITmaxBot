from .client import PyrusClient
from .mapper import map_task
from typing import Optional


class PyrusService:
    def __init__(self, client: PyrusClient):
        self.client = client

    async def get_task(self, task_id: int):
        raw = await self.client._request(
            "GET",
            f"{self.client.base_url}/tasks/{task_id}"
        )

        return map_task(raw)

    async def create_task(self, data: dict):
        return await self.client.create_ticket(data)

    # async def add_comment(self, task_id: int, text: str):
    #     return await self.client.add_comment(task_id, text)

    async def get_contractor_id_by_inn(self, inn: str) -> Optional[int]:
        """Возвращает ID контрагента по ИНН"""
        try:
            url = f"{self.client.base_url}/forms/2306222/register"

            payload = {
                "filters": [
                    {
                        "id": 2,  # ID поля ИНН
                        "type": "equals",
                        "value": inn
                    }
                ]
            }

            response = await self.client._request("POST", url, json_data=payload)

            if response and response.get('tasks'):
                return response['tasks'][0].get('id')

            return None

        except Exception as e:
            print(f"Ошибка поиска ID контрагента: {e}")
            return None

    async def get_contractor_info(self, inn: str) -> Optional[dict]:
        """Возвращает ID и название компании по ИНН"""
        try:
            url = f"{self.client.base_url}/forms/2306222/register"

            payload = {
                "filters": [
                    {
                        "id": 2,
                        "type": "equals",
                        "value": inn
                    }
                ]
            }

            response = await self.client._request("POST", url, json_data=payload)

            if response and response.get('tasks'):
                task = response['tasks'][0]

                # Ищем название компании (поле ID 10)
                company_name = None
                for field in task.get('fields', []):
                    if field.get('id') == 10:
                        company_name = field.get('value')
                        break

                return {
                    'id': task.get('id'),
                    'name': company_name,
                    'inn': inn
                }

            return None

        except Exception as e:
            print(f"Ошибка: {e}")
            return None