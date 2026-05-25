from fastapi.testclient import TestClient

from backend.conftest import auth_headers, create_poi


def test_create_poi(client: TestClient, admin_headers):
    response = client.post(
        "/pois/",
        headers=admin_headers,
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


def test_read_pois_requires_auth(client: TestClient, admin_headers):
    assert client.get("/pois/").status_code == 401

    create_poi(client, admin_headers, latitude=10.0, longitude=20.0)
    create_poi(client, admin_headers, latitude=11.0, longitude=21.0)

    response = client.get("/pois/", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_poi(client: TestClient, admin_headers):
    poi = create_poi(client, admin_headers, latitude=0.0, longitude=0.0)
    poi_id = poi["id"]

    update_response = client.patch(
        f"/pois/{poi_id}", headers=admin_headers, json={"description": "destroyed"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "destroyed"


def test_delete_poi(client: TestClient, admin_headers):
    poi = create_poi(client, admin_headers, latitude=0.0, longitude=0.0)
    poi_id = poi["id"]

    delete_response = client.delete(f"/pois/{poi_id}", headers=admin_headers)
    assert delete_response.status_code == 204

    read_response = client.get(f"/pois/{poi_id}", headers=admin_headers)
    assert read_response.status_code == 404
