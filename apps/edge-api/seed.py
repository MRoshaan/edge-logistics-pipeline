import asyncio
import random
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.settings import get_settings


async def seed_drivers() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database_name]
    drivers = db["drivers"]

    await client.admin.command("ping")
    await drivers.create_index([("location", "2dsphere")])

    base_lon = 67.0011
    base_lat = 24.8607

    docs = []
    for idx in range(1, 16):
        lon = base_lon + random.uniform(-0.08, 0.08)
        lat = base_lat + random.uniform(-0.06, 0.06)
        docs.append(
            {
                "name": f"Driver {idx}",
                "status": "online",
                "location": {
                    "type": "Point",
                    "coordinates": [round(lon, 6), round(lat, 6)],
                },
                "updatedAt": datetime.now(timezone.utc),
            }
        )

    await drivers.delete_many({"name": {"$regex": r"^Driver\s+\d+$"}})
    result = await drivers.insert_many(docs)
    print(f"Inserted {len(result.inserted_ids)} Karachi drivers.")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed_drivers())
