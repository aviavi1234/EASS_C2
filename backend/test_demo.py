"""Regression tests for the EX3 grader demo script."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from scripts import demo


def test_demo_uses_auth_headers_for_protected_endpoints():
    """Filtered list and weekly digest require JWT — demo must pass headers."""
    calls: list[tuple[str, dict | None]] = []

    def fake_get(url: str, **kwargs):
        calls.append((url, kwargs.get("headers")))
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = [] if url.endswith("/pois/") else {"total_pois": 0}
        response.raise_for_status = MagicMock()
        return response

    def fake_post(url: str, **kwargs):
        response = MagicMock()
        response.status_code = 200
        if url.endswith("/auth/token"):
            response.json.return_value = {"access_token": "demo-token"}
        else:
            response.json.return_value = {"id": 1}
        response.raise_for_status = MagicMock()
        return response

    with patch.object(demo, "wait_for_api"), patch.object(
        demo.httpx, "get", side_effect=fake_get
    ), patch.object(demo.httpx, "post", side_effect=fake_post), patch.object(
        demo.subprocess, "run", return_value=MagicMock(returncode=0)
    ):
        demo.main()

    auth_header = {"Authorization": "Bearer demo-token"}
    filtered_call = next(c for c in calls if c[0].endswith("/pois/"))
    digest_call = next(c for c in calls if c[0].endswith("/digest/weekly"))

    assert filtered_call[1] == auth_header
    assert digest_call[1] == auth_header
