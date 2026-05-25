"""Map interaction helpers (pure math, no NiceGUI dependency)."""

from __future__ import annotations

import math

_ICON_HIT_RADIUS_PX = 19.0


def mercator_pixel_xy(lat: float, lng: float, zoom: int) -> tuple[float, float]:
    sin_y = min(max(math.sin(math.radians(lat)), -0.9999), 0.9999)
    scale = 256.0 * (2.0**zoom)
    x = (lng + 180.0) / 360.0 * scale
    y = (0.5 - math.log((1.0 + sin_y) / (1.0 - sin_y)) / (4.0 * math.pi)) * scale
    return x, y


def poi_hit_by_icon_click(
    click_lat: float,
    click_lng: float,
    zoom: int,
    pois: list[dict],
    radius_px: float = _ICON_HIT_RADIUS_PX,
) -> dict | None:
    zx, zy = mercator_pixel_xy(click_lat, click_lng, zoom)
    best: dict | None = None
    best_d = radius_px + 1.0
    for poi in pois:
        px, py = mercator_pixel_xy(float(poi["latitude"]), float(poi["longitude"]), zoom)
        distance = math.hypot(px - zx, py - zy)
        if distance <= radius_px and distance < best_d:
            best_d = distance
            best = poi
    return best


def unit_hit_by_icon_click(
    click_lat: float,
    click_lng: float,
    zoom: int,
    units: list[dict],
    radius_px: float = _ICON_HIT_RADIUS_PX,
) -> dict | None:
    zx, zy = mercator_pixel_xy(click_lat, click_lng, zoom)
    best: dict | None = None
    best_d = radius_px + 1.0
    for unit in units:
        lat = float(unit.get("unit_lat") or 0.0)
        lng = float(unit.get("unit_lng") or 0.0)
        px, py = mercator_pixel_xy(lat, lng, zoom)
        distance = math.hypot(px - zx, py - zy)
        if distance <= radius_px and distance < best_d:
            best_d = distance
            best = unit
    return best
