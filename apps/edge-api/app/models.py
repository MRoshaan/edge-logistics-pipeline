from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class DriverStatus(str, Enum):
    online = "online"
    active = "active"
    busy = "busy"
    offline = "offline"


class GeoPoint(BaseModel):
    type: str = Field(default="Point")
    coordinates: list[float] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="GeoJSON coordinates [longitude, latitude]",
    )

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value != "Point":
            raise ValueError("GeoJSON type must be 'Point'")
        return value

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, value: list[float]) -> list[float]:
        lon, lat = value
        if not (-180 <= lon <= 180):
            raise ValueError("longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("latitude must be between -90 and 90")
        return value


Meters = Annotated[float, Field(ge=0)]


class DriverTelemetryIn(BaseModel):
    driverId: str = Field(min_length=3, max_length=64)
    status: DriverStatus
    location: GeoPoint
    heading: float | None = Field(default=None, ge=0, le=360)
    speedKph: float | None = Field(default=None, ge=0, le=240)
    timestamp: datetime


class NearestDriverOut(BaseModel):
    id: str
    driverId: str
    status: DriverStatus
    distanceMeters: Meters
    location: GeoPoint
    updatedAt: datetime


class NearestDriversResponse(BaseModel):
    center: GeoPoint
    limit: int = Field(ge=1, le=50)
    drivers: list[NearestDriverOut]


class NearestDriversQuery(BaseModel):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    maxDistanceMeters: int = Field(default=3000, ge=100, le=50000)
    limit: int = Field(default=5, ge=1, le=50)


class DriverLocationUpdateIn(BaseModel):
    driverId: str = Field(min_length=3, max_length=128)
    status: DriverStatus = DriverStatus.online
    location: GeoPoint
    speedKph: float | None = Field(default=None, ge=0, le=240)
    heading: float | None = Field(default=None, ge=0, le=360)


class DriverLocationEvent(BaseModel):
    type: str = "driver.location.updated"
    timestamp: datetime
    payload: NearestDriverOut
