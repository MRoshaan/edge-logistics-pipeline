from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.settings import get_settings

settings = get_settings()
client = AsyncIOMotorClient(settings.mongodb_uri)


def get_database() -> AsyncIOMotorDatabase:
    return client[settings.mongodb_database_name]


async def ping_database() -> None:
    await client.admin.command("ping")


async def close_database() -> None:
    client.close()
