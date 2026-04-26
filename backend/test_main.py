import os
import pytest
from pathlib import Path


TEST_DB_FILE = "test_c2_database.db"
os.environ["C2_DB_FILE"] = TEST_DB_FILE

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client

    db.engine.dispose()
    test_db_path = Path(db.file_name)
    if test_db_path.exists():
        test_db_path.unlink()


def test_create_poi(client: TestClient):
    response = client.post(
        "/pois/",
        json={
            "latitude": 32.0853,
            "longitude": 34.7818,
            "poi_type": "tank",
            "description": "Hostile spotted",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["latitude"] == 32.0853
    assert data["poi_type"] == "tank"
    assert data["status"] == "active"
    assert "id" in data


def test_read_pois(client: TestClient):
    client.post("/pois/", json={"latitude": 10.0, "longitude": 20.0})
    client.post("/pois/", json={"latitude": 11.0, "longitude": 21.0})

    response = client.get("/pois/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_update_poi(client: TestClient):
    create_response = client.post(
        "/pois/", json={"latitude": 0.0, "longitude": 0.0, "status": "active"}
    )
    poi_id = create_response.json()["id"]

    update_response = client.patch(f"/pois/{poi_id}", json={"status": "destroyed"})
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "destroyed"


def test_delete_poi(client: TestClient):
    create_response = client.post("/pois/", json={"latitude": 0.0, "longitude": 0.0})
    poi_id = create_response.json()["id"]

    delete_response = client.delete(f"/pois/{poi_id}")
    assert delete_response.status_code == 204

    read_response = client.get(f"/pois/{poi_id}")
    assert read_response.status_code == 404
