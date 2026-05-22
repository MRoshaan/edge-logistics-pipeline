from fastapi import APIRouter

from app.models import DriverTelemetryIn, GeoPoint, NearestDriversQuery, NearestDriversResponse
from app.services.database import get_database

router = APIRouter()
db = get_database()


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
    drivers = []
    for doc in documents:
        drivers.append(
            {
                "id": str(doc["_id"]),
                "driverId": doc.get("driverId", str(doc["_id"])),
                "status": doc["status"],
                "distanceMeters": float(doc["distanceMeters"]),
                "location": doc["location"],
                "updatedAt": doc["updatedAt"],
            }
        )

    return NearestDriversResponse(
        center=GeoPoint(type="Point", coordinates=[query.longitude, query.latitude]),
        limit=5,
        drivers=drivers,
    )
