import pytest

from frontend.shared.map_helpers import mercator_pixel_xy, poi_hit_by_icon_click


def test_mercator_pixel_xy_center():
    x, y = mercator_pixel_xy(0.0, 0.0, zoom=10)
    scale = 256.0 * (2.0**10)
    assert x == pytest.approx(scale / 2.0)
    assert y == pytest.approx(scale / 2.0)


def test_poi_hit_by_icon_click_finds_nearby_marker():
    pois = [{"id": 1, "latitude": 32.0, "longitude": 34.0}]
    hit = poi_hit_by_icon_click(32.0, 34.0, zoom=12, pois=pois)
    assert hit is not None
    assert hit["id"] == 1


def test_poi_hit_by_icon_click_ignores_far_clicks():
    pois = [{"id": 1, "latitude": 32.0, "longitude": 34.0}]
    hit = poi_hit_by_icon_click(40.0, 40.0, zoom=12, pois=pois)
    assert hit is None
