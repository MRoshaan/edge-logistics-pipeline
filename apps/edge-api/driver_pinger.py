import asyncio
import json
import math
import random
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from app.settings import get_settings

settings = get_settings()
TICK_SECONDS = 3
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


async def load_driver_ids() -> list[str]:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database_name]
    rows = await db["drivers"].find({}, {"_id": 1, "driverId": 1}).to_list(length=15)
    client.close()
    ids = []
    for row in rows:
        ids.append(row.get("driverId") or str(row["_id"]))
    return ids


async def ping_loop() -> None:
    driver_ids = await load_driver_ids()
    if not driver_ids:
        print("No drivers found. Seed first: python seed.py")
        return

    print(f"Driver simulator booted with {len(driver_ids)} drivers")
    random.seed(42)

    phases = {driver_id: random.uniform(0, math.pi * 2) for driver_id in driver_ids}

    seq = 1
    while True:
        now = datetime.now(timezone.utc)
        t = now.timestamp()
        for idx, driver_id in enumerate(driver_ids):
            phase = phases[driver_id]
            lon = 67.0011 + 0.06 * math.cos((t / 35) + phase) + random.uniform(-0.0015, 0.0015)
            lat = 24.8607 + 0.04 * math.sin((t / 28) + phase) + random.uniform(-0.0015, 0.0015)

            payload = {
                "eventId": f"sim-{driver_id}-{seq}",
                "seq": seq,
                "type": "driver.location.updated",
                "timestamp": now.isoformat(),
                "payload": {
                    "id": driver_id,
                    "driverId": driver_id,
                    "status": "online",
                    "distanceMeters": 0,
                    "location": {
                        "type": "Point",
                        "coordinates": [
                            round(clamp(lon, 66.88, 67.18), 6),
                            round(clamp(lat, 24.74, 24.98), 6),
                        ],
                    },
                    "speedKph": round(random.uniform(18, 58), 2),
                    "heading": round((t * 7 + idx * 13) % 360, 2),
                    "updatedAt": now.isoformat(),
                },
            }

            try:
                await redis_client.publish("fleet:updates", json.dumps(payload))
            except Exception as err:
                print("simulator publish error", str(err))

            seq += 1

        print(f"broadcast tick {now.isoformat()} published {len(driver_ids)} drivers")
        await asyncio.sleep(TICK_SECONDS)


async def shutdown() -> None:
    await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(ping_loop())
    finally:
        asyncio.run(shutdown())
