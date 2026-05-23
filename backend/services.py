from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from backend.models import PointOfInterest, WeeklyDigest

# Priority weights by type code (admin-defined types fall back to 20.0)
_TYPE_WEIGHT: dict[str, float] = {
    "tank": 80.0,
    "infentry": 60.0,
    "unknowns": 20.0,
}


def compute_priority_score(poi: PointOfInterest) -> float:
    """Simple deterministic priority for async refresh demos."""
    code = (poi.poi_type or "Unknowns").lower()
    base = _TYPE_WEIGHT.get(code, 20.0)
    return base


def refresh_poi_priority(session: Session, poi_id: int) -> PointOfInterest | None:
    poi = session.get(PointOfInterest, poi_id)
    if not poi:
        return None
    poi.priority_score = compute_priority_score(poi)
    poi.last_refreshed_at = datetime.now(timezone.utc)
    poi.updated_at = datetime.now(timezone.utc)
    session.add(poi)
    session.commit()
    session.refresh(poi)
    return poi


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_weekly_digest(session: Session) -> WeeklyDigest:
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    pois = session.exec(select(PointOfInterest)).all()
    recent = [p for p in pois if _as_utc(p.created_at) >= week_start]
    active = 0
    inactive = 0
    destroyed = 0
    investigating = 0
    top = sorted(recent, key=lambda p: p.priority_score, reverse=True)[:5]
    top_payload = [
        {
            "id": p.id,
            "poi_type": p.poi_type,
            "priority_score": p.priority_score,
        }
        for p in top
    ]
    return WeeklyDigest(
        week_start=week_start,
        total_pois=len(recent),
        top_priority=top_payload,
    )
