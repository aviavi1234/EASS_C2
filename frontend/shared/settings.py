"""Pure helpers for client-side user preferences (browser storage)."""

from __future__ import annotations

from datetime import datetime, timezone

DEFAULT_ACTIVITY_TIERS: list[dict] = [
    {"id": 1, "max_minutes": 5, "color": "#00ff00"},
    {"id": 2, "max_minutes": 15, "color": "#ffff00"},
    {"id": 3, "max_minutes": 60, "color": "#ffa500"},
    {"id": 4, "max_minutes": None, "color": "#ff0000"},
]


def normalize_activity_tiers(tiers: list[dict]) -> list[dict]:
    return sorted(
        tiers,
        key=lambda tier: tier["max_minutes"] if tier["max_minutes"] is not None else float("inf"),
    )


def resolve_activity_color(
    updated_at: datetime,
    tiers: list[dict] | None = None,
    *,
    now: datetime | None = None,
) -> str:
    tiers = tiers or DEFAULT_ACTIVITY_TIERS
    now = now or datetime.now(timezone.utc)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    age_min = (now - updated_at).total_seconds() / 60.0
    for tier in normalize_activity_tiers(tiers):
        max_minutes = tier.get("max_minutes")
        if max_minutes is None:
            return tier["color"]
        if age_min < max_minutes:
            return tier["color"]
    return tiers[-1]["color"] if tiers else "#888888"


def format_datetime(
    value: str | None,
    *,
    date_format: str = "dd.mm.yyyy",
    time_format: str = "24 hrs",
) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        date_str = dt.strftime("%d.%m.%Y") if date_format == "dd.mm.yyyy" else dt.strftime("%m.%d.%Y")
        time_str = dt.strftime("%H:%M:%S") if time_format == "24 hrs" else dt.strftime("%I:%M:%S %p")
        return f"{date_str} {time_str} UTC"
    except ValueError:
        return str(value)
