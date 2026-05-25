import asyncio
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from app.settings import get_settings

settings = get_settings()

TICK_SECONDS = 3
EARTH_RADIUS_M = 6_371_000
OSRM_BASE_URL = "http://router.project-osrm.org"

# Requested Karachi bounds
MIN_LAT, MAX_LAT = 24.8, 24.95
MIN_LON, MAX_LON = 66.95, 67.15

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


@dataclass
class SimDriver:
    driver_id: str
    driver_name: str
    plate_number: str
    vehicle_type: str
    speed_mps: float
    current_lat: float
    current_lon: float
    heading_deg: float
    current_route: list[tuple[float, float]]  # (lon, lat)
    route_index: int  # next waypoint index


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1r = math.radians(lat1)
    lat2r = math.radians(lat2)
    dlat = lat2r - lat1r
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    theta = math.degrees(math.atan2(y, x))
    return (theta + 360) % 360


def destination_point(lat_deg: float, lon_deg: float, bearing_degrees: float, distance_m: float) -> tuple[float, float]:
    lat1 = math.radians(lat_deg)
    lon1 = math.radians(lon_deg)
    brng = math.radians(bearing_degrees)
    ang_dist = distance_m / EARTH_RADIUS_M

    lat2 = math.asin(
        math.sin(lat1) * math.cos(ang_dist)
        + math.cos(lat1) * math.sin(ang_dist) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(ang_dist) * math.cos(lat1),
        math.cos(ang_dist) - math.sin(lat1) * math.sin(lat2),
    )

    return math.degrees(lat2), ((math.degrees(lon2) + 540) % 360) - 180


def random_karachi_point() -> tuple[float, float]:
    return (
        random.uniform(MIN_LAT, MAX_LAT),
        random.uniform(MIN_LON, MAX_LON),
    )


def _fetch_osrm_route_blocking(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> list[tuple[float, float]] | None:
    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{start_lon},{start_lat};{end_lon},{end_lat}"
        f"?overview=full&geometries=geojson"
    )

    response = requests.get(url, timeout=12)
    if response.status_code == 429:
        raise RuntimeError("OSRM_RATE_LIMIT")
    if response.status_code >= 500:
        raise RuntimeError(f"OSRM_SERVER_{response.status_code}")
    if response.status_code != 200:
        return None

    payload = response.json()
    routes = payload.get("routes") or []
    if not routes:
        return None

    coords = routes[0].get("geometry", {}).get("coordinates") or []
    if len(coords) < 2:
        return None

    clean: list[tuple[float, float]] = []
    for item in coords:
        if not isinstance(item, list) or len(item) != 2:
            continue
        clean.append((float(item[0]), float(item[1])))

    return clean if len(clean) >= 2 else None


async def fetch_osrm_route_with_retry(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> list[tuple[float, float]] | None:
    backoff = 1.5
    for _ in range(7):
        try:
            route = await asyncio.to_thread(
                _fetch_osrm_route_blocking,
                start_lat,
                start_lon,
                end_lat,
                end_lon,
            )
            if route:
                return route
            await asyncio.sleep(min(backoff, 6))
            backoff *= 1.5
        except RuntimeError as err:
            if "OSRM_RATE_LIMIT" in str(err):
                await asyncio.sleep(min(backoff + random.uniform(0.3, 1.0), 8))
                backoff *= 1.7
            else:
                await asyncio.sleep(min(backoff, 6))
                backoff *= 1.5
        except Exception:
            await asyncio.sleep(min(backoff, 6))
            backoff *= 1.5

    return None


async def generate_route_for_driver(
    start_lat: float,
    start_lon: float,
) -> list[tuple[float, float]] | None:
    for _ in range(10):
        end_lat, end_lon = random_karachi_point()
        route = await fetch_osrm_route_with_retry(start_lat, start_lon, end_lat, end_lon)
        if route:
            return route
    return None


async def load_driver_ids() -> list[dict[str, str]]:
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database_name]
    rows = await db["drivers"].find(
        {},
        {
            "_id": 1,
            "driverId": 1,
            "driverName": 1,
            "plateNumber": 1,
            "vehicleType": 1,
        },
    ).to_list(length=15)
    client.close()

    ids: list[dict[str, str]] = []
    for row in rows:
        driver_id = row.get("driverId") or str(row["_id"])
        ids.append(
            {
                "driverId": driver_id,
                "driverName": row.get("driverName", f"Driver {driver_id}"),
                "plateNumber": row.get("plateNumber", f"KHI-{random.randint(1000, 9999)}"),
                "vehicleType": row.get("vehicleType", random.choice(["Car", "Bike"])),
            }
        )
    return ids


async def build_sim_drivers() -> list[SimDriver]:
    driver_ids = await load_driver_ids()
    if not driver_ids:
        return []

    sim_drivers: list[SimDriver] = []
    for entry in driver_ids:
        driver_id = entry["driverId"]
        rng = random.Random(driver_id)
        start_lat, start_lon = random_karachi_point()

        route = await generate_route_for_driver(start_lat, start_lon)
        if not route:
            continue

        start_lon_route, start_lat_route = route[0]
        speed_kph = rng.uniform(34, 46)
        speed_mps = speed_kph * 1000 / 3600
        vehicle_type = entry.get("vehicleType", rng.choice(["Car", "Bike"]))

        initial_heading = bearing_deg(
            start_lat_route,
            start_lon_route,
            route[1][1],
            route[1][0],
        )

        sim_drivers.append(
            SimDriver(
                driver_id=driver_id,
                driver_name=entry.get("driverName", f"Driver {driver_id}"),
                plate_number=entry.get("plateNumber", f"KHI-{rng.randint(1000, 9999)}"),
                vehicle_type=vehicle_type,
                speed_mps=speed_mps,
                current_lat=start_lat_route,
                current_lon=start_lon_route,
                heading_deg=initial_heading,
                current_route=route,
                route_index=1,
            )
        )

    return sim_drivers


async def ensure_route(driver: SimDriver) -> None:
    if driver.route_index < len(driver.current_route):
        return

    new_route = await generate_route_for_driver(driver.current_lat, driver.current_lon)
    if new_route and len(new_route) >= 2:
        driver.current_route = new_route
        driver.route_index = 1


async def move_driver_along_route(driver: SimDriver, dt_seconds: float) -> None:
    remaining_m = driver.speed_mps * dt_seconds
    prev_lat = driver.current_lat
    prev_lon = driver.current_lon

    await ensure_route(driver)

    while remaining_m > 0:
        if driver.route_index >= len(driver.current_route):
            await ensure_route(driver)
            if driver.route_index >= len(driver.current_route):
                break

        waypoint_lon, waypoint_lat = driver.current_route[driver.route_index]
        segment_m = haversine_m(driver.current_lat, driver.current_lon, waypoint_lat, waypoint_lon)

        if segment_m < 0.5:
            driver.current_lat = waypoint_lat
            driver.current_lon = waypoint_lon
            driver.route_index += 1
            continue

        if remaining_m >= segment_m:
            driver.current_lat = waypoint_lat
            driver.current_lon = waypoint_lon
            driver.route_index += 1
            remaining_m -= segment_m
            continue

        brng = bearing_deg(driver.current_lat, driver.current_lon, waypoint_lat, waypoint_lon)
        driver.current_lat, driver.current_lon = destination_point(
            driver.current_lat,
            driver.current_lon,
            brng,
            remaining_m,
        )
        remaining_m = 0

    driver.heading_deg = bearing_deg(prev_lat, prev_lon, driver.current_lat, driver.current_lon)


async def ping_loop() -> None:
    drivers = await build_sim_drivers()
    if not drivers:
        print("No routable drivers found. Check DB seed and OSRM availability.")
        return

    print(f"Map-matched simulator booted with {len(drivers)} drivers")
    seq = 1

    while True:
        now = datetime.now(timezone.utc)

        for driver in drivers:
            await move_driver_along_route(driver, TICK_SECONDS)

            payload = {
                "eventId": f"sim-{driver.driver_id}-{seq}",
                "seq": seq,
                "type": "driver.location.updated",
                "timestamp": now.isoformat(),
                "payload": {
                    "id": driver.driver_id,
                    "driverId": driver.driver_id,
                    "driverName": driver.driver_name,
                    "plateNumber": driver.plate_number,
                    "status": "online",
                    "distanceMeters": 0,
                    "latitude": round(driver.current_lat, 6),
                    "longitude": round(driver.current_lon, 6),
                    "heading": round(driver.heading_deg, 2),
                    "speedKph": round(driver.speed_mps * 3.6, 2),
                    "vehicleType": driver.vehicle_type,
                    "location": {
                        "type": "Point",
                        "coordinates": [round(driver.current_lon, 6), round(driver.current_lat, 6)],
                    },
                    "updatedAt": now.isoformat(),
                },
            }

            try:
                await redis_client.publish("fleet:updates", json.dumps(payload))
            except Exception as err:
                print("simulator publish error", str(err))

            seq += 1

        print(f"tick {now.isoformat()} published {len(drivers)} map-matched updates")
        await asyncio.sleep(TICK_SECONDS)


async def shutdown() -> None:
    await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(ping_loop())
    finally:
        asyncio.run(shutdown())
