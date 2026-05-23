from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.database import db  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(name="client")
def client_fixture():
    test_db_path = Path(db.file_name)
    if test_db_path.exists():
        test_db_path.unlink()
    with TestClient(app) as client:
        yield client

    db.engine.dispose()
    if test_db_path.exists():
        test_db_path.unlink()


def _auth_headers(client: TestClient) -> dict:
    response = client.post(
        "/auth/token", json={"username": "admin", "password": "admin1234"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_poi(client: TestClient):
    response = client.post(
        "/pois/",
        headers=_auth_headers(client),
            json={
                "latitude": 32.0853,
                "longitude": 34.7818,
                "poi_type": "Tank",
                "description": "Hostile spotted",
            },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["latitude"] == 32.0853
    assert data["poi_type"] == "Tank"
    assert data["created_by_username"] == "admin"
    assert "id" in data


def test_read_pois_requires_auth(client: TestClient):
    assert client.get("/pois/").status_code == 401

    headers = _auth_headers(client)
    client.post(
        "/pois/", headers=headers, json={"latitude": 10.0, "longitude": 20.0}
    )
    client.post(
        "/pois/", headers=headers, json={"latitude": 11.0, "longitude": 21.0}
    )

    response = client.get("/pois/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_poi(client: TestClient):
    headers = _auth_headers(client)
    create_response = client.post(
        "/pois/",
        headers=headers,
        json={"latitude": 0.0, "longitude": 0.0},
    )
    poi_id = create_response.json()["id"]

    update_response = client.patch(
        f"/pois/{poi_id}", headers=headers, json={"description": "destroyed"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "destroyed"


def test_delete_poi(client: TestClient):
    headers = _auth_headers(client)
    create_response = client.post(
        "/pois/", headers=headers, json={"latitude": 0.0, "longitude": 0.0}
    )
    poi_id = create_response.json()["id"]

    delete_response = client.delete(f"/pois/{poi_id}", headers=headers)
    assert delete_response.status_code == 204

    read_response = client.get(f"/pois/{poi_id}", headers=headers)
    assert read_response.status_code == 404
