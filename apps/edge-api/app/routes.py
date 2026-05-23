from datetime import datetime, timezone
from itertools import count
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi import status

from app.models import (
    DriverLocationEvent,
    DispatchAssignIn,
    DriverStatus,
    DriverTelemetryIn,
    GeoPoint,
    NearestDriverOut,
    NearestDriversQuery,
    NearestDriversResponse,
)
from app.services.database import get_database, redis_client
router = APIRouter()
db = get_database()
EVENT_SEQ = count(1)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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


@router.post("/dispatch/assign")
async def assign_driver(payload: DispatchAssignIn) -> dict:
    lock_key = f"lock:driver:{payload.driverId}"
    lock_value = payload.dispatcherId
    lock_acquired = await redis_client.set(lock_key, lock_value, nx=True, px=10000)

    if not lock_acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Driver is currently being assigned by another dispatcher",
        )

    now = datetime.now(timezone.utc)
    result = await db["drivers"].update_one(
        {"driverId": payload.driverId},
        {
            "$set": {
                "status": DriverStatus.busy.value,
                "updatedAt": now,
                "assignedBy": payload.dispatcherId,
            }
        },
    )

    doc = await db["drivers"].find_one({"driverId": payload.driverId})
    if doc:
        event_payload = NearestDriverOut(
            id=str(doc.get("_id", payload.driverId)),
            driverId=doc.get("driverId", payload.driverId),
            status=DriverStatus(doc.get("status", DriverStatus.busy.value)),
            distanceMeters=0,
            location=doc.get("location", {"type": "Point", "coordinates": [67.0011, 24.8607]}),
            updatedAt=doc.get("updatedAt", now),
        )
        event = DriverLocationEvent(
            eventId=str(uuid4()),
            seq=next(EVENT_SEQ),
            timestamp=now,
            type="driver.status.updated",
            payload=event_payload,
        )
        await redis_client.publish("fleet:updates", event.model_dump_json())

    return {
        "acknowledged": True,
        "matchedCount": result.matched_count,
        "modifiedCount": result.modified_count,
        "lockKey": lock_key,
        "dispatcherId": payload.dispatcherId,
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
                "query": {"status": {"$in": ["active", "online", "busy"]}},
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
