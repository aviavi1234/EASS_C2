from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.database import db
from backend.main import app


@pytest.fixture(name="client")
def client_fixture():
    path = Path(db.file_name)
    if path.exists():
        path.unlink()
    with TestClient(app) as client:
        yield client
    db.engine.dispose()
    if path.exists():
        path.unlink()


def _login(client: TestClient) -> str:
    response = client.post(
        "/auth/token", json={"username": "admin", "password": "admin1234"}
    )
    return response.json()["access_token"]


def test_filter_by_type_status_and_description(client: TestClient):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/pois/",
        headers=headers,
        json={
            "latitude": 1,
            "longitude": 1,
            "poi_type": "Tank",
            "description": "Alpha convoy",
        },
    )
    client.post(
        "/pois/",
        headers=headers,
        json={
            "latitude": 2,
            "longitude": 2,
            "poi_type": "Unknowns",
            "description": "Old depot",
        },
    )

    response = client.get(
        "/pois/",
        headers=headers,
        params={"poi_type": "Tank", "description_contains": "convoy"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["poi_type"] == "Tank"


def test_weekly_digest(client: TestClient):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/pois/",
        headers=headers,
        json={"latitude": 1, "longitude": 1, "poi_type": "Tank"},
    )
    digest = client.get("/pois/digest/weekly", headers=headers)
    assert digest.status_code == 200
    body = digest.json()
    assert body["total_pois"] >= 1
    assert "top_priority" in body
