from workers import WorkerEntrypoint
from workers.asgi import fetch

from app.main import app


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        return await fetch(app, request)
