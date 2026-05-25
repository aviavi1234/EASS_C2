from datetime import timedelta

from fastapi.testclient import TestClient
from jose import jwt
from sqlmodel import Session, select

from backend.auth import create_access_token
from backend.config import get_settings
from backend.conftest import auth_headers, create_poi, create_user, login
from backend.database import db
from backend.models import User


def test_expired_token_rejected(client: TestClient):
    with Session(db.engine) as session:
        writer = session.exec(select(User).where(User.username == "admin")).first()
    expired = create_access_token(user=writer, expires_delta=timedelta(seconds=-30))
    response = client.post(
        "/pois/",
        headers=auth_headers(expired),
        json={"latitude": 1.0, "longitude": 2.0},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_missing_scope_rejected(client: TestClient):
    from datetime import datetime, timezone

    settings = get_settings()
    payload = {
        "sub": "admin",
        "role": "user",
        "permission": "read_write",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    bad_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    response = client.post(
        "/pois/",
        headers=auth_headers(bad_token),
        json={"latitude": 1.0, "longitude": 2.0},
    )
    assert response.status_code == 403
    assert "scope" in response.json()["detail"].lower()


def test_read_only_cannot_create(client: TestClient, admin_headers):
    create_user(client, admin_headers, "reader", "reader-pass", permission="read_only")
    token = login(client, "reader", "reader-pass")
    response = client.post(
        "/pois/",
        headers=auth_headers(token),
        json={"latitude": 0.0, "longitude": 0.0, "poi_type": "Tank"},
    )
    assert response.status_code == 403


def test_user_cannot_delete_others_poi(client: TestClient, admin_headers):
    create_user(client, admin_headers, "writer", "writer-pass", permission="read_write")
    create_user(client, admin_headers, "reader", "reader-pass", permission="read_only")

    writer_token = login(client, "writer", "writer-pass")
    poi = create_poi(client, auth_headers(writer_token))
    poi_id = poi["id"]

    reader_token = login(client, "reader", "reader-pass")
    response = client.delete(f"/pois/{poi_id}", headers=auth_headers(reader_token))
    assert response.status_code == 403

    admin_delete = client.delete(
        f"/pois/{poi_id}",
        headers=admin_headers,
    )
    assert admin_delete.status_code == 204


def test_admin_can_manage_users(client: TestClient, admin_headers):
    create = client.post(
        "/users/",
        headers=admin_headers,
        json={
            "username": "tempuser",
            "password": "temp-pass",
            "role": "user",
            "permission": "read_only",
        },
    )
    assert create.status_code == 201
    user_id = create.json()["id"]

    patch = client.patch(
        f"/users/{user_id}",
        headers=admin_headers,
        json={"permission": "read_write"},
    )
    assert patch.status_code == 200
    assert patch.json()["permission"] == "read_write"

    delete = client.delete(f"/users/{user_id}", headers=admin_headers)
    assert delete.status_code == 204
