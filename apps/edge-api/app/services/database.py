from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.settings import get_settings

settings = get_settings()
client = AsyncIOMotorClient(settings.mongodb_uri)
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def get_database() -> AsyncIOMotorDatabase:
    return client[settings.mongodb_database_name]


async def ping_database() -> None:
    await client.admin.command("ping")
    try:
        await redis_client.ping()
    except RedisError:
        pass


async def close_database() -> None:
    await redis_client.aclose()
    client.close()
