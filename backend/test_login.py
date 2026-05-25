from fastapi.testclient import TestClient

from backend.conftest import auth_headers, create_user, login


def test_login_success(client: TestClient):
    response = client.post(
        "/auth/token",
        json={"username": "admin", "password": "admin1234"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["username"] == "admin"
    assert data["role"] == "admin"
    assert data["permission"] == "read_write"
    assert "access_token" in data
    assert "id" in data


def test_login_invalid_password(client: TestClient):
    response = client.post(
        "/auth/token",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_login_unknown_user(client: TestClient):
    response = client.post(
        "/auth/token",
        json={"username": "nobody", "password": "secret"},
    )
    assert response.status_code == 401


def test_login_returns_unit_fields(client: TestClient, admin_headers):
    user_id = client.get("/users/", headers=admin_headers).json()[0]["id"]
    patch = client.patch(
        f"/users/{user_id}",
        headers=admin_headers,
        json={
            "unit_name": "Alpha",
            "unit_type": "Tank",
            "unit_description": "Lead element",
            "unit_lat": 32.1,
            "unit_lng": 34.8,
            "show_location": True,
        },
    )
    assert patch.status_code == 200

    login = client.post(
        "/auth/token",
        json={"username": "admin", "password": "admin1234"},
    )
    body = login.json()
    assert body["unit_name"] == "Alpha"
    assert body["unit_type"] == "Tank"
    assert body["show_location"] is True
    assert body["unit_lat"] == 32.1


def test_user_login_includes_permission(client: TestClient, admin_headers):
    create_user(client, admin_headers, "writer2", "writer2-pass", permission="read_write")
    response = client.post(
        "/auth/token",
        json={"username": "writer2", "password": "writer2-pass"},
    )
    assert response.status_code == 200
    assert response.json()["permission"] == "read_write"
    assert response.json()["role"] == "user"


def test_missing_bearer_token_rejected(client: TestClient):
    response = client.get("/pois/")
    assert response.status_code == 401
