from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class POIType(str, Enum):
    BUILDING = "building"
    SOLDIER = "soldier"
    TANK = "tank"
    VEHICLE = "vehicle"
    UNKNOWN = "unknown"


class POIStatus(str, Enum):
    ACTIVE = "active"
    DESTROYED = "destroyed"
    INVESTIGATING = "investigating"


class PointOfInterestBase(SQLModel):
    latitude: float
    longitude: float
    elevation: Optional[float] = 0.0
    poi_type: POIType = POIType.UNKNOWN
    status: POIStatus = POIStatus.ACTIVE
    description: Optional[str] = None


class PointOfInterest(PointOfInterestBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PointOfInterestCreate(PointOfInterestBase):
    pass


class PointOfInterestUpdate(SQLModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    poi_type: Optional[POIType] = None
    status: Optional[POIStatus] = None
    description: Optional[str] = None
