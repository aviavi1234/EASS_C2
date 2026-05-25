from contextlib import asynccontextmanager
from datetime import datetime, timezone
import re
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from backend.auth import (
    authenticate_user,
    can_modify_poi,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    require_write_access,
    verify_service_key,
)
from backend.database import db
from backend.middleware import RateLimitMiddleware
from backend.models import (
    LoginRequest,
    Permission,
    PoiTypeCreate,
    PoiTypeDefinition,
    PoiTypePublic,
    PoiTypeUpdate,
    PointOfInterest,
    PointOfInterestCreate,
    PointOfInterestRead,
    PointOfInterestUpdate,
    TokenResponse,
    User,
    UserCreate,
    UserPublic,
    UserRole,
    UserUpdate,
    WeeklyDigest,
)
from backend.poi_icons import (
    ALLOWED_ICON_SUFFIXES,
    icons_directory,
    user_icons_directory,
    safe_icon_basename,
)
from scripts.init.seed import (
    seed_poi_types,
    seed_users,
)
from backend.services import build_weekly_digest, compute_priority_score, refresh_poi_priority

def _poi_type_to_public(row: PoiTypeDefinition) -> PoiTypePublic:
    icon_url = None
    if row.icon_filename:
        icon_url = f"/poi-types/icons/{row.icon_filename}"
    return PoiTypePublic(
        id=row.id,
        label=row.label,
        icon_url=icon_url,
    )


def _user_to_public(user: User) -> UserPublic:
    unit_icon_url = None
    if user.unit_icon_filename:
        unit_icon_url = f"/users/icons/{user.unit_icon_filename}"
    permission = user.permission
    if user.role == UserRole.ADMIN:
        permission = Permission.READ_WRITE
    return UserPublic(
        id=user.id,
        username=user.username,
        role=user.role,
        permission=permission,
        requires_setup=user.requires_setup,
        unit_name=user.unit_name,
        unit_type=user.unit_type,
        unit_description=user.unit_description,
        unit_icon_url=unit_icon_url,
        unit_lat=user.unit_lat,
        unit_lng=user.unit_lng,
        unit_last_online=user.unit_last_online,
        show_location=user.show_location,
    )


def _require_known_poi_type(session: Session, label: str) -> None:
    l = label.strip()
    row = session.exec(select(PoiTypeDefinition).where(PoiTypeDefinition.label == l)).first()
    if not row:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown poi_type '{l}'. Add it under Settings (admin) or pick an existing type.",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.create_db_and_tables()
    with Session(db.engine) as session:
        seed_users(session)
        seed_poi_types(session)
    yield


app = FastAPI(title="Command & Control API", lifespan=lifespan)
app.add_middleware(RateLimitMiddleware)


def _poi_to_read(session: Session, poi: PointOfInterest, user_id: int | None = None) -> PointOfInterestRead:
    return PointOfInterestRead.model_validate(poi)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/token", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(db.get_session)):
    user = authenticate_user(session, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user=user)
    pub = _user_to_public(user)
    return TokenResponse(
        access_token=token,
        **pub.model_dump()
    )


@app.get("/poi-types/", response_model=List[PoiTypePublic])
def list_poi_types(
    session: Session = Depends(db.get_session),
    _: User = Depends(get_current_user),
):
    rows = session.exec(select(PoiTypeDefinition)).all()
    return [_poi_type_to_public(r) for r in rows]


@app.post("/poi-types/", response_model=PoiTypePublic, status_code=201)
def create_poi_type(
    body: PoiTypeCreate,
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
):
    label = body.label.strip()
    if session.exec(select(PoiTypeDefinition).where(PoiTypeDefinition.label == label)).first():
        raise HTTPException(status_code=409, detail="Type label already exists")
    row = PoiTypeDefinition(label=label)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _poi_type_to_public(row)


@app.patch("/poi-types/{type_id}", response_model=PoiTypePublic)
def update_poi_type(
    type_id: int,
    body: PoiTypeUpdate,
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
):
    row = session.get(PoiTypeDefinition, type_id)
    if not row:
        raise HTTPException(status_code=404, detail="POI type not found")
    old_label = row.label
    if body.label is not None:
        new_label = body.label.strip()
        if new_label != old_label:
            if session.exec(select(PoiTypeDefinition).where(PoiTypeDefinition.label == new_label)).first():
                raise HTTPException(status_code=409, detail="Type label already exists")
            for poi in session.exec(select(PointOfInterest).where(PointOfInterest.poi_type == old_label)).all():
                poi.poi_type = new_label
                session.add(poi)
            row.label = new_label
    session.add(row)
    session.commit()
    session.refresh(row)
    return _poi_type_to_public(row)


@app.delete("/poi-types/{type_id}", status_code=204)
def delete_poi_type(
    type_id: int,
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
):
    row = session.get(PoiTypeDefinition, type_id)
    if not row:
        raise HTTPException(status_code=404, detail="POI type not found")
    in_use = session.exec(
        select(PointOfInterest).where(PointOfInterest.poi_type == row.label)
    ).first()
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete a type that is still used by one or more points",
        )
    if row.icon_filename and safe_icon_basename(row.icon_filename):
        path = icons_directory() / row.icon_filename
        if path.is_file():
            path.unlink()
    session.delete(row)
    session.commit()


@app.delete("/poi-types/{type_id}/icon", response_model=PoiTypePublic)
def delete_poi_type_icon(
    type_id: int,
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
):
    poi_type = session.get(PoiTypeDefinition, type_id)
    if not poi_type:
        raise HTTPException(status_code=404, detail="POI type not found")

    if poi_type.icon_filename and safe_icon_basename(poi_type.icon_filename):
        old = icons_directory() / poi_type.icon_filename
        if old.is_file():
            old.unlink()

    poi_type.icon_filename = None
    session.add(poi_type)
    session.commit()
    session.refresh(poi_type)
    return _poi_type_to_public(poi_type)

@app.get("/poi-types/icons/{filename}")
def get_poi_type_icon(filename: str):
    if not safe_icon_basename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = icons_directory() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Icon not found")
    return FileResponse(path)


@app.post("/poi-types/{type_id}/icon", response_model=PoiTypePublic)
async def upload_poi_type_icon(
    type_id: int,
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
    file: UploadFile = File(...),
):
    row = session.get(PoiTypeDefinition, type_id)
    if not row:
        raise HTTPException(status_code=404, detail="POI type not found")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_ICON_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_ICON_SUFFIXES))}",
        )
    new_name = f"{type_id}_{uuid.uuid4().hex}{suffix}"
    dest = icons_directory() / new_name
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 2 MB)")
    dest.write_bytes(data)
    if row.icon_filename and safe_icon_basename(row.icon_filename):
        old = icons_directory() / row.icon_filename
        if old.is_file() and old.name != new_name:
            old.unlink()
    row.icon_filename = new_name
    session.add(row)
    session.commit()
    session.refresh(row)
    return _poi_type_to_public(row)


@app.get("/users/", response_model=List[UserPublic])
def list_users(
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
):
    users = session.exec(select(User)).all()
    return [_user_to_public(u) for u in users]


@app.post("/users/", response_model=UserPublic, status_code=201)
def create_user(
    body: UserCreate,
    session: Session = Depends(db.get_session),
    _: User = Depends(require_admin),
):
    if session.exec(select(User).where(User.username == body.username)).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    if body.role == UserRole.ADMIN:
        permission = None
    else:
        permission = body.permission
    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
        permission=permission,
        requires_setup=False,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_public(user)


@app.patch("/users/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    body: UserUpdate,
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this user")

    if body.username is not None:
        if body.username != user.username and session.exec(select(User).where(User.username == body.username)).first():
            raise HTTPException(status_code=409, detail="Username already exists")
        user.username = body.username

    if body.permission is not None:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not authorized to modify permissions")
        if user.role == UserRole.ADMIN:
            raise HTTPException(status_code=400, detail="Cannot set permission on admin users")
        user.permission = body.permission

    if body.password:
        user.hashed_password = hash_password(body.password)
        
    if body.requires_setup is not None:
        user.requires_setup = body.requires_setup

    if body.unit_name is not None:
        user.unit_name = body.unit_name
    if body.unit_type is not None:
        user.unit_type = body.unit_type
    if body.unit_description is not None:
        user.unit_description = body.unit_description
    if body.unit_lat is not None:
        user.unit_lat = body.unit_lat
    if body.unit_lng is not None:
        user.unit_lng = body.unit_lng
    if body.unit_last_online is not None:
        user.unit_last_online = body.unit_last_online
    if body.show_location is not None:
        user.show_location = body.show_location

    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_public(user)


@app.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    session: Session = Depends(db.get_session),
    current_admin: User = Depends(require_admin),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    session.delete(user)
    session.commit()


@app.post("/pois/", response_model=PointOfInterestRead, status_code=201)
def create_poi(
    poi: PointOfInterestCreate,
    session: Session = Depends(db.get_session),
    current_user: User = Depends(require_write_access),
):
    payload = poi.model_dump()
    payload["poi_type"] = (payload.get("poi_type") or "Unknowns").strip()
    _require_known_poi_type(session, payload["poi_type"])
    db_poi = PointOfInterest(
        **payload,
        created_by_user_id=current_user.id,
        created_by_username=current_user.username,
    )
    db_poi.priority_score = compute_priority_score(db_poi)
    session.add(db_poi)
    session.commit()
    session.refresh(db_poi)
    return _poi_to_read(session, db_poi, current_user.id)


@app.get("/pois/", response_model=List[PointOfInterestRead])
def read_pois(
    skip: int = 0,
    limit: int = 100,
    poi_type: Optional[str] = None,
    description_contains: Optional[str] = Query(default=None),
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    statement = select(PointOfInterest)
    if poi_type is not None:
        statement = statement.where(PointOfInterest.poi_type == poi_type.strip())
    pois = session.exec(statement.offset(skip).limit(limit)).all()
    if description_contains:
        needle = description_contains.lower()
        pois = [
            p
            for p in pois
            if p.description and needle in p.description.lower()
        ]
    return [_poi_to_read(session, p, current_user.id) for p in pois]


@app.get("/pois/digest/weekly", response_model=WeeklyDigest)
def weekly_digest(
    session: Session = Depends(db.get_session),
    _: User = Depends(get_current_user),
):
    return build_weekly_digest(session)


@app.post("/pois/{poi_id}/refresh", response_model=PointOfInterestRead)
def refresh_poi_endpoint(
    poi_id: int,
    session: Session = Depends(db.get_session),
    _: None = Depends(verify_service_key),
):
    poi = refresh_poi_priority(session, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="Point of Interest not found")
    return _poi_to_read(session, poi, None)


@app.get("/pois/{poi_id}", response_model=PointOfInterestRead)
def read_poi(
    poi_id: int,
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    poi = session.get(PointOfInterest, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="Point of Interest not found")
    return _poi_to_read(session, poi, current_user.id)


@app.patch("/pois/{poi_id}", response_model=PointOfInterestRead)
def update_poi(
    poi_id: int,
    poi_update: PointOfInterestUpdate,
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    db_poi = session.get(PointOfInterest, poi_id)
    if not db_poi:
        raise HTTPException(status_code=404, detail="Point of Interest not found")
    if not can_modify_poi(current_user, db_poi):
        raise HTTPException(
            status_code=403,
            detail="You can only modify your own points unless you are an admin",
        )

    update_data = poi_update.model_dump(exclude_unset=True)
    if "poi_type" in update_data and update_data["poi_type"] is not None:
        update_data["poi_type"] = str(update_data["poi_type"]).strip()
        _require_known_poi_type(session, update_data["poi_type"])
    for key, value in update_data.items():
        setattr(db_poi, key, value)

    db_poi.updated_at = datetime.now(timezone.utc)
    db_poi.priority_score = compute_priority_score(db_poi)

    session.add(db_poi)
    session.commit()
    session.refresh(db_poi)
    return _poi_to_read(session, db_poi, current_user.id)


@app.delete("/pois/{poi_id}", status_code=204)
def delete_poi(
    poi_id: int,
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    poi = session.get(PointOfInterest, poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="Point of Interest not found")
    if not can_modify_poi(current_user, poi):
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own points unless you are an admin",
        )
    session.delete(poi)
    session.commit()


@app.post("/users/me/ping")
def ping_user(
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    current_user.unit_last_online = datetime.now(timezone.utc)
    session.add(current_user)
    session.commit()
    return {"status": "ok"}


@app.post("/users/me/offline")
def go_offline(
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    """Clear online presence so the unit disappears from the map immediately on logout."""
    current_user.unit_last_online = None
    session.add(current_user)
    session.commit()
    return {"status": "ok"}

@app.get("/units/", response_model=List[UserPublic])
def list_active_units(
    session: Session = Depends(db.get_session),
    _: User = Depends(get_current_user),
):
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=90)
    users = session.exec(
        select(User)
        .where(User.show_location == True)
        .where(User.unit_last_online != None)
        .where(User.unit_last_online >= cutoff)
    ).all()
    return [_user_to_public(u) for u in users]


@app.post("/users/{user_id}/icon", response_model=UserPublic)
async def upload_user_unit_icon(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this user")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_ICON_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_ICON_SUFFIXES))}",
        )
    new_name = f"user_{user_id}_{uuid.uuid4().hex}{suffix}"
    dest = user_icons_directory() / new_name
    data = await file.read()
    if len(data) > 2_000_000:
        raise HTTPException(status_code=400, detail="File too large (max 2 MB)")
    dest.write_bytes(data)
    
    if user.unit_icon_filename and safe_icon_basename(user.unit_icon_filename):
        old = user_icons_directory() / user.unit_icon_filename
        if old.is_file() and old.name != new_name:
            old.unlink()
            
    user.unit_icon_filename = new_name
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_public(user)


@app.delete("/users/{user_id}/icon", response_model=UserPublic)
def delete_user_unit_icon(
    user_id: int,
    session: Session = Depends(db.get_session),
    current_user: User = Depends(get_current_user),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this user")

    if user.unit_icon_filename and safe_icon_basename(user.unit_icon_filename):
        old = user_icons_directory() / user.unit_icon_filename
        if old.is_file():
            old.unlink()
            
    user.unit_icon_filename = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return _user_to_public(user)

@app.get("/users/icons/{filename}")
def get_user_unit_icon(filename: str):
    if not safe_icon_basename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = user_icons_directory() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Icon not found")
    return FileResponse(path)
