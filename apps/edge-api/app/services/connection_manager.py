from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable

from fastapi import WebSocket
from redis.exceptions import RedisError

from app.services.database import redis_client


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._listener_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def start_pubsub_listener(self) -> None:
        if self._listener_task and not self._listener_task.done():
            return
        self._stop_event.clear()
        self._listener_task = asyncio.create_task(self._listen_pubsub())

    async def stop_pubsub_listener(self) -> None:
        self._stop_event.set()
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

    async def broadcast_json(self, message: dict) -> None:
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        self._drop_connections(stale)

    def _drop_connections(self, sockets: Iterable[WebSocket]) -> None:
        for socket in sockets:
            self._connections.discard(socket)

    async def _listen_pubsub(self) -> None:
        while not self._stop_event.is_set():
            pubsub = redis_client.pubsub()
            try:
                await pubsub.subscribe("fleet:updates")
                while not self._stop_event.is_set():
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if not message:
                        continue

                    raw_data = message.get("data")
                    if not isinstance(raw_data, str):
                        continue

                    try:
                        payload = json.loads(raw_data)
                    except json.JSONDecodeError:
                        continue

                    if isinstance(payload, dict):
                        await self.broadcast_json(payload)
            except RedisError:
                await asyncio.sleep(1.5)
            finally:
                try:
                    await pubsub.unsubscribe("fleet:updates")
                except Exception:
                    pass
                await pubsub.close()


manager = ConnectionManager()
