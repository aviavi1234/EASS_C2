from fastapi.testclient import TestClient

from backend.conftest import auth_headers, login


def test_filter_by_type_and_description(client: TestClient, admin_headers):
    client.post(
        "/pois/",
        headers=admin_headers,
        json={
            "latitude": 1,
            "longitude": 1,
            "poi_type": "Tank",
            "description": "Alpha convoy",
        },
    )
    client.post(
        "/pois/",
        headers=admin_headers,
        json={
            "latitude": 2,
            "longitude": 2,
            "poi_type": "Unknowns",
            "description": "Old depot",
        },
    )

    response = client.get(
        "/pois/",
        headers=admin_headers,
        params={"poi_type": "Tank", "description_contains": "convoy"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["poi_type"] == "Tank"


def test_weekly_digest(client: TestClient, admin_headers):
    client.post(
        "/pois/",
        headers=admin_headers,
        json={"latitude": 1, "longitude": 1, "poi_type": "Tank"},
    )
    digest = client.get("/pois/digest/weekly", headers=admin_headers)
    assert digest.status_code == 200
    body = digest.json()
    assert body["total_pois"] >= 1
    assert "top_priority" in body
