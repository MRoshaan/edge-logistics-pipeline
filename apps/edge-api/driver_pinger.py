import asyncio
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from app.settings import get_settings

settings = get_settings()
TICK_SECONDS = 3
EARTH_RADIUS_M = 6_371_000

# Karachi operating bounds
MIN_LON, MAX_LON = 66.88, 67.18
MIN_LAT, MAX_LAT = 24.74, 24.98

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


@dataclass
class SimDriver:
    driver_id: str
    lat: float
    lon: float
    heading_deg: float
    speed_kph: float
    vehicle_type: str


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def normalize_heading(degrees: float) -> float:
    return degrees % 360


def destination_point(lat_deg: float, lon_deg: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    """Great-circle destination point from start location, bearing, and distance."""
    lat1 = math.radians(lat_deg)
    lon1 = math.radians(lon_deg)
    bearing = math.radians(bearing_deg)
    angular_distance = distance_m / EARTH_RADIUS_M

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )

    latitude_out = math.degrees(lat2)
    longitude_out = (math.degrees(lon2) + 540) % 360 - 180
    return latitude_out, longitude_out


def step_driver(driver: SimDriver, dt_seconds: float) -> None:
    distance_m = driver.speed_kph * 1000 / 3600 * dt_seconds
    next_lat, next_lon = destination_point(driver.lat, driver.lon, driver.heading_deg, distance_m)

    bounced = False
    if next_lon < MIN_LON or next_lon > MAX_LON:
        driver.heading_deg = normalize_heading(180 - driver.heading_deg)
        bounced = True
    if next_lat < MIN_LAT or next_lat > MAX_LAT:
        driver.heading_deg = normalize_heading(-driver.heading_deg)
        bounced = True

    if bounced:
        next_lat, next_lon = destination_point(driver.lat, driver.lon, driver.heading_deg, distance_m)
    else:
        # subtle steering drift to avoid robotic lines
        driver.heading_deg = normalize_heading(driver.heading_deg + random.uniform(-1.2, 1.2))

    driver.lat = clamp(next_lat, MIN_LAT, MAX_LAT)
    driver.lon = clamp(next_lon, MIN_LON, MAX_LON)


async def load_sim_drivers() -> list[SimDriver]:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database_name]
    rows = await db["drivers"].find({}, {"_id": 1, "driverId": 1, "location": 1}).to_list(length=15)
    client.close()

    drivers: list[SimDriver] = []
    for row in rows:
        driver_id = row.get("driverId") or str(row["_id"])
        coords = row.get("location", {}).get("coordinates", [67.0011, 24.8607])
        lon, lat = float(coords[0]), float(coords[1])

        seed_rng = random.Random(driver_id)
        heading_deg = seed_rng.uniform(0, 360)
        speed_kph = seed_rng.uniform(36, 44)
        vehicle_type = seed_rng.choice(["sedan", "bike", "rickshaw"])

        drivers.append(
            SimDriver(
                driver_id=driver_id,
                lat=lat,
                lon=lon,
                heading_deg=heading_deg,
                speed_kph=speed_kph,
                vehicle_type=vehicle_type,
            )
        )

    return drivers


async def ping_loop() -> None:
    drivers = await load_sim_drivers()
    if not drivers:
        print("No drivers found. Seed first: python seed.py")
        return

    print(f"Vector simulator booted with {len(drivers)} drivers")
    seq = 1

    while True:
        now = datetime.now(timezone.utc)
        for driver in drivers:
            step_driver(driver, TICK_SECONDS)

            payload = {
                "eventId": f"sim-{driver.driver_id}-{seq}",
                "seq": seq,
                "type": "driver.location.updated",
                "timestamp": now.isoformat(),
                "payload": {
                    "id": driver.driver_id,
                    "driverId": driver.driver_id,
                    "status": "online",
                    "distanceMeters": 0,
                    "location": {
                        "type": "Point",
                        "coordinates": [round(driver.lon, 6), round(driver.lat, 6)],
                    },
                    "speedKph": round(driver.speed_kph, 2),
                    "heading": round(driver.heading_deg, 2),
                    "vehicleType": driver.vehicle_type,
                    "updatedAt": now.isoformat(),
                },
            }

            try:
                await redis_client.publish("fleet:updates", json.dumps(payload))
            except Exception as err:
                print("simulator publish error", str(err))

            seq += 1

        print(f"tick {now.isoformat()} published {len(drivers)} vector updates")
        await asyncio.sleep(TICK_SECONDS)


async def shutdown() -> None:
    await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(ping_loop())
    finally:
        asyncio.run(shutdown())
