"""Tests for async POI refresh (Session 09 / EX3)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.conftest import admin_headers, auth_headers, create_poi, login
from backend.refresh_queue import idempotency_key, job_payload, parse_job
from scripts.refresh import run_refresh


def test_refresh_endpoint_requires_service_key(client: TestClient, admin_headers):
    poi = create_poi(client, admin_headers)
    user_token = login(client, "admin", "admin1234")

    assert client.post(
        f"/pois/{poi['id']}/refresh",
        headers=auth_headers(user_token),
    ).status_code == 401

    assert client.post(f"/pois/{poi['id']}/refresh").status_code == 401


def test_refresh_endpoint_updates_priority(client: TestClient, admin_headers):
    poi = create_poi(client, admin_headers, poi_type="Tank")
    settings = get_settings()

    response = client.post(
        f"/pois/{poi['id']}/refresh",
        headers={"Authorization": f"Bearer {settings.service_api_key}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["priority_score"] == 80.0
    assert body["last_refreshed_at"] is not None


def test_refresh_endpoint_not_found(client: TestClient):
    settings = get_settings()
    response = client.post(
        "/pois/99999/refresh",
        headers={"Authorization": f"Bearer {settings.service_api_key}"},
    )
    assert response.status_code == 404


def test_refresh_queue_helpers():
    key = idempotency_key("demo-run", 7)
    assert key == "refresh:run:demo-run:poi:7"
    raw = job_payload("demo-run", 7)
    parsed = parse_job(raw)
    assert parsed["poi_id"] == 7
    assert parsed["idempotency_key"] == key
    assert parsed["run_id"] == "demo-run"


@pytest.mark.anyio
async def test_orchestrator_enqueues_and_skips_idempotent_jobs():
    redis_client = MagicMock()
    redis_client.get.return_value = None

    async def fake_login(api_base, username, password):
        return "token"

    async def fake_fetch(api_base, token):
        return [1, 2]

    with patch("scripts.refresh._login", fake_login), patch(
        "scripts.refresh._fetch_poi_ids", fake_fetch
    ), patch("scripts.refresh.redis.from_url", return_value=redis_client):
        summary = await run_refresh(
            api_base="http://testserver",
            run_id="test-run",
            concurrency=2,
            username="admin",
            password="admin1234",
            redis_url="redis://localhost:6379/0",
        )

    assert summary == {"enqueued": 2, "skipped": 0, "total": 2}
    assert redis_client.rpush.call_count == 2


@pytest.mark.anyio
async def test_orchestrator_skips_already_refreshed_pois():
    redis_client = MagicMock()
    redis_client.get.return_value = "1"

    async def fake_login(api_base, username, password):
        return "token"

    async def fake_fetch(api_base, token):
        return [5]

    with patch("scripts.refresh._login", fake_login), patch(
        "scripts.refresh._fetch_poi_ids", fake_fetch
    ), patch("scripts.refresh.redis.from_url", return_value=redis_client):
        summary = await run_refresh(
            api_base="http://testserver",
            run_id="test-run",
            concurrency=1,
            username="admin",
            password="admin1234",
            redis_url="redis://localhost:6379/0",
        )

    assert summary == {"enqueued": 0, "skipped": 1, "total": 1}
    redis_client.rpush.assert_not_called()
