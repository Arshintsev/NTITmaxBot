from .client import PyrusClient
from .mapper import map_task


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

    async def add_comment(self, task_id: int, text: str):
        return await self.client.add_comment(task_id, text)