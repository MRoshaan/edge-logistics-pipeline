from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.models import DriverTelemetryIn, GeoPoint, NearestDriverOut, NearestDriversQuery
from app.settings import get_settings


class AtlasDataAPIClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "api-key": self.settings.atlas_data_api_key,
        }

    async def upsert_driver_telemetry(self, payload: DriverTelemetryIn) -> dict:
        body = {
            "dataSource": self.settings.atlas_data_source,
            "database": self.settings.atlas_database,
            "collection": self.settings.atlas_collection,
            "filter": {"driverId": payload.driverId},
            "update": {
                "$set": {
                    "driverId": payload.driverId,
                    "status": payload.status.value,
                    "location": payload.location.model_dump(),
                    "heading": payload.heading,
                    "speedKph": payload.speedKph,
                    "updatedAt": payload.timestamp.astimezone(timezone.utc).isoformat(),
                }
            },
            "upsert": True,
        }

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{self.settings.atlas_data_api_url}/action/updateOne",
                headers=self._headers,
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def get_nearest_active_drivers(
        self, query: NearestDriversQuery
    ) -> list[NearestDriverOut]:
        body = {
            "dataSource": self.settings.atlas_data_source,
            "database": self.settings.atlas_database,
            "collection": self.settings.atlas_collection,
            "pipeline": [
                {
                    "$geoNear": {
                        "near": {
                            "type": "Point",
                            "coordinates": [query.longitude, query.latitude],
                        },
                        "distanceField": "distanceMeters",
                        "maxDistance": query.maxDistanceMeters,
                        "spherical": True,
                        "query": {"status": "active"},
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "driverId": 1,
                        "status": 1,
                        "location": 1,
                        "distanceMeters": 1,
                        "updatedAt": 1,
                    }
                },
                {"$limit": query.limit},
            ],
        }

        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{self.settings.atlas_data_api_url}/action/aggregate",
                headers=self._headers,
                json=body,
            )
            response.raise_for_status()
            documents = response.json().get("documents", [])

        drivers: list[NearestDriverOut] = []
        for doc in documents:
            updated_at_raw = doc.get("updatedAt")
            if isinstance(updated_at_raw, str):
                updated_at = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
            else:
                updated_at = datetime.now(timezone.utc)

            drivers.append(
                NearestDriverOut(
                    driverId=doc["driverId"],
                    status=doc["status"],
                    distanceMeters=float(doc["distanceMeters"]),
                    location=GeoPoint(**doc["location"]),
                    updatedAt=updated_at,
                )
            )

        return drivers
