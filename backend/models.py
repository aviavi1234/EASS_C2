from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class Permission(str, Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    permission: Optional[Permission] = Field(default=Permission.READ_ONLY)
    requires_setup: bool = Field(default=False)


class UserCreate(SQLModel):
    username: str
    password: str
    role: UserRole = UserRole.USER
    permission: Permission = Permission.READ_ONLY


class UserUpdate(SQLModel):
    username: Optional[str] = None
    permission: Optional[Permission] = None
    password: Optional[str] = None
    requires_setup: Optional[bool] = None


class UserPublic(SQLModel):
    id: int
    username: str
    role: UserRole
    permission: Optional[Permission] = None
    requires_setup: bool = False


class LoginRequest(SQLModel):
    username: str
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    username: str
    role: UserRole
    permission: Optional[Permission] = None
    requires_setup: bool = False


class PoiTypeDefinition(SQLModel, table=True):
    """Admin-configurable POI categories."""

    __tablename__ = "poi_type_definition"

    id: Optional[int] = Field(default=None, primary_key=True)
    label: str = Field(unique=True, index=True, max_length=128)
    icon_filename: Optional[str] = Field(default=None, max_length=256)


class PoiTypeCreate(SQLModel):
    label: str


class PoiTypeUpdate(SQLModel):
    label: Optional[str] = None


class PoiTypePublic(SQLModel):
    id: int
    label: str
    icon_url: Optional[str] = None


class PointOfInterestBase(SQLModel):
    latitude: float
    longitude: float
    elevation: Optional[float] = 0.0
    poi_type: str = "Unknowns"
    description: Optional[str] = None


class PointOfInterest(PointOfInterestBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_by_user_id: int = Field(foreign_key="user.id")
    created_by_username: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    priority_score: float = Field(default=0.0)
    last_refreshed_at: Optional[datetime] = None


class PointOfInterestCreate(PointOfInterestBase):
    pass


class PointOfInterestUpdate(SQLModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation: Optional[float] = None
    poi_type: Optional[str] = None
    description: Optional[str] = None


class PointOfInterestRead(PointOfInterestBase):
    id: int
    created_by_user_id: int
    created_by_username: str
    created_at: datetime
    updated_at: datetime
    priority_score: float = 0.0
    last_refreshed_at: Optional[datetime] = None
    color: Optional[str] = None


class WeeklyDigest(SQLModel):
    week_start: datetime
    total_pois: int
    top_priority: list[dict]
