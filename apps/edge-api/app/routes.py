from fastapi import APIRouter

from app.models import DriverTelemetryIn, GeoPoint, NearestDriversQuery, NearestDriversResponse
from app.services.atlas_data_api import AtlasDataAPIClient

router = APIRouter()
atlas = AtlasDataAPIClient()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/telemetry")
async def ingest_telemetry(payload: DriverTelemetryIn) -> dict:
    result = await atlas.upsert_driver_telemetry(payload)
    return {
        "acknowledged": True,
        "matchedCount": result.get("matchedCount", 0),
        "modifiedCount": result.get("modifiedCount", 0),
        "upsertedId": result.get("upsertedId"),
    }


@router.get("/dispatch/nearest", response_model=NearestDriversResponse)
async def nearest_drivers(
    longitude: float,
    latitude: float,
    maxDistanceMeters: int = 3000,
    limit: int = 5,
) -> NearestDriversResponse:
    query = NearestDriversQuery(
        longitude=longitude,
        latitude=latitude,
        maxDistanceMeters=maxDistanceMeters,
        limit=limit,
    )
    drivers = await atlas.get_nearest_active_drivers(query)

    return NearestDriversResponse(
        center=GeoPoint(type="Point", coordinates=[query.longitude, query.latitude]),
        limit=query.limit,
        drivers=drivers,
    )
