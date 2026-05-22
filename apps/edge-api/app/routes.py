from datetime import datetime, timezone
from itertools import count
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException

from app.models import (
    DriverLocationEvent,
    DriverLocationUpdateIn,
    DriverStatus,
    DriverTelemetryIn,
    GeoPoint,
    NearestDriverOut,
    NearestDriversQuery,
    NearestDriversResponse,
)
from app.services.connection_manager import manager
from app.services.database import get_database
from app.settings import get_settings

router = APIRouter()
db = get_database()
settings = get_settings()
EVENT_SEQ = count(1)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "wsActiveConnections": str(manager.active_count)}


@router.post("/telemetry")
async def ingest_telemetry(payload: DriverTelemetryIn) -> dict:
    result = await db["drivers"].update_one(
        {"driverId": payload.driverId},
        {
            "$set": {
                "driverId": payload.driverId,
                "status": payload.status.value,
                "location": payload.location.model_dump(),
                "heading": payload.heading,
                "speedKph": payload.speedKph,
                "updatedAt": payload.timestamp,
            }
        },
        upsert=True,
    )
    return {
        "acknowledged": True,
        "matchedCount": result.matched_count,
        "modifiedCount": result.modified_count,
        "upsertedId": str(result.upserted_id) if result.upserted_id else None,
    }


@router.post("/telemetry/simulated")
async def ingest_simulated_telemetry(
    payload: DriverLocationUpdateIn,
    x_simulator_token: str = Header(default=""),
) -> dict:
    if x_simulator_token != settings.simulator_api_token:
        raise HTTPException(status_code=401, detail="Invalid simulator token")

    now = datetime.now(timezone.utc)
    result = await db["drivers"].update_one(
        {"driverId": payload.driverId},
        {
            "$set": {
                "driverId": payload.driverId,
                "status": payload.status.value,
                "location": payload.location.model_dump(),
                "speedKph": payload.speedKph,
                "heading": payload.heading,
                "updatedAt": now,
            }
        },
        upsert=True,
    )

    event_payload = NearestDriverOut(
        id=payload.driverId,
        driverId=payload.driverId,
        status=DriverStatus(payload.status),
        distanceMeters=0,
        location=payload.location,
        updatedAt=now,
    )
    event = DriverLocationEvent(
        eventId=str(uuid4()),
        seq=next(EVENT_SEQ),
        timestamp=now,
        payload=event_payload,
    )
    await manager.broadcast_json(event.model_dump(mode="json"))

    return {
        "acknowledged": True,
        "matchedCount": result.matched_count,
        "modifiedCount": result.modified_count,
        "upsertedId": str(result.upserted_id) if result.upserted_id else None,
        "broadcasted": True,
    }


@router.get("/drivers/nearby", response_model=NearestDriversResponse)
async def nearest_drivers(
    longitude: float,
    latitude: float,
    maxDistanceMeters: int = 3000,
) -> NearestDriversResponse:
    query = NearestDriversQuery(
        longitude=longitude,
        latitude=latitude,
        maxDistanceMeters=maxDistanceMeters,
        limit=5,
    )
    pipeline = [
        {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [query.longitude, query.latitude]},
                "distanceField": "distanceMeters",
                "maxDistance": query.maxDistanceMeters,
                "spherical": True,
                "query": {"status": {"$in": ["active", "online"]}},
            }
        },
        {
            "$project": {
                "_id": 1,
                "driverId": 1,
                "status": 1,
                "location": 1,
                "distanceMeters": 1,
                "updatedAt": 1,
            }
        },
        {"$limit": 5},
    ]

    documents = await db["drivers"].aggregate(pipeline).to_list(length=5)
    drivers: list[NearestDriverOut] = []
    for doc in documents:
        drivers.append(
            NearestDriverOut(
                id=str(doc["_id"]),
                driverId=doc.get("driverId", str(doc["_id"])),
                status=DriverStatus(doc["status"]),
                distanceMeters=float(doc["distanceMeters"]),
                location=doc["location"],
                updatedAt=doc["updatedAt"],
            )
        )

    return NearestDriversResponse(
        center=GeoPoint(type="Point", coordinates=[query.longitude, query.latitude]),
        limit=5,
        drivers=drivers,
    )
