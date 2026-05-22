import asyncio
import math
import random
from datetime import datetime, timezone

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from app.settings import get_settings

settings = get_settings()
BASE_URL = "http://127.0.0.1:8000"
TICK_SECONDS = 3


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

    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            now = datetime.now(timezone.utc)
            t = now.timestamp()
            for idx, driver_id in enumerate(driver_ids):
                phase = phases[driver_id]
                lon = 67.0011 + 0.06 * math.cos((t / 35) + phase) + random.uniform(-0.0015, 0.0015)
                lat = 24.8607 + 0.04 * math.sin((t / 28) + phase) + random.uniform(-0.0015, 0.0015)

                payload = {
                    "driverId": driver_id,
                    "status": "online",
                    "speedKph": round(random.uniform(18, 58), 2),
                    "heading": round((t * 7 + idx * 13) % 360, 2),
                    "location": {
                        "type": "Point",
                        "coordinates": [round(clamp(lon, 66.88, 67.18), 6), round(clamp(lat, 24.74, 24.98), 6)],
                    },
                }
                try:
                    response = await client.post(
                        f"{BASE_URL}/api/v1/telemetry/simulated",
                        json=payload,
                        headers={"x-simulator-token": settings.simulator_api_token},
                    )
                    if response.is_error:
                        print("simulator post failed", response.status_code, response.text)
                except Exception as err:
                    print("simulator request error", str(err))

            print(f"broadcast tick {now.isoformat()} updated {len(driver_ids)} drivers")
            await asyncio.sleep(TICK_SECONDS)


if __name__ == "__main__":
    asyncio.run(ping_loop())
