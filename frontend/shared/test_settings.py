from datetime import datetime, timedelta, timezone

from frontend.shared.settings import (
    DEFAULT_ACTIVITY_TIERS,
    format_datetime,
    normalize_activity_tiers,
    resolve_activity_color,
)


def test_normalize_activity_tiers_sorts_by_max_minutes():
    tiers = [
        {"id": 4, "max_minutes": None, "color": "#ff0000"},
        {"id": 1, "max_minutes": 5, "color": "#00ff00"},
        {"id": 3, "max_minutes": 60, "color": "#ffa500"},
    ]
    ordered = normalize_activity_tiers(tiers)
    assert [t["max_minutes"] for t in ordered[:3]] == [5, 60, None]


def test_resolve_activity_color_uses_custom_tiers():
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    updated = now - timedelta(minutes=10)
    tiers = [
        {"id": 1, "max_minutes": 5, "color": "#00ff00"},
        {"id": 2, "max_minutes": 15, "color": "#ffff00"},
        {"id": 3, "max_minutes": None, "color": "#ff0000"},
    ]
    assert resolve_activity_color(updated, tiers, now=now) == "#ffff00"


def test_resolve_activity_color_inactivity_tier():
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    updated = now - timedelta(hours=3)
    assert resolve_activity_color(updated, DEFAULT_ACTIVITY_TIERS, now=now) == "#ff0000"


def test_format_datetime_respects_date_and_time_formats():
    value = "2026-05-25T10:30:00+00:00"
    assert format_datetime(value, date_format="dd.mm.yyyy", time_format="24 hrs") == "25.05.2026 10:30:00 UTC"
    assert format_datetime(value, date_format="mm.dd.yyyy", time_format="12 hrs") == "05.25.2026 10:30:00 AM UTC"


def test_format_datetime_empty_value():
    assert format_datetime(None) == "—"
    assert format_datetime("") == "—"


def test_saved_activity_tiers_round_trip():
    custom = [
        {"id": 1, "max_minutes": 2, "color": "#111111"},
        {"id": 2, "max_minutes": None, "color": "#222222"},
    ]
    stored = normalize_activity_tiers(custom.copy())
    now = datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc)
    updated = now - timedelta(minutes=1)
    assert resolve_activity_color(updated, stored, now=now) == "#111111"
