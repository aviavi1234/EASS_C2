from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from backend.auth import create_access_token
from backend.config import get_settings
from backend.database import db
from backend.main import app
from backend.models import User


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


def _token_for(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/token", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_expired_token_rejected(client: TestClient):
    from sqlmodel import Session, select

    with Session(db.engine) as session:
        writer = session.exec(select(User).where(User.username == "admin")).first()
    expired = create_access_token(user=writer, expires_delta=timedelta(seconds=-30))
    response = client.post(
        "/pois/",
        headers={"Authorization": f"Bearer {expired}"},
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
        headers={"Authorization": f"Bearer {bad_token}"},
        json={"latitude": 1.0, "longitude": 2.0},
    )
    assert response.status_code == 403
    assert "scope" in response.json()["detail"].lower()


def test_read_only_cannot_create(client: TestClient):
    admin_token = _token_for(client, "admin", "admin1234")
    client.post(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"username": "reader", "password": "reader-pass", "role": "user", "permission": "read_only"}
    )
    token = _token_for(client, "reader", "reader-pass")
    response = client.post(
        "/pois/",
        headers={"Authorization": f"Bearer {token}"},
        json={"latitude": 0.0, "longitude": 0.0},
    )
    assert response.status_code == 403


def test_user_cannot_delete_others_poi(client: TestClient):
    admin_token = _token_for(client, "admin", "admin1234")
    client.post(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"username": "writer", "password": "writer-pass", "role": "user", "permission": "read_write"}
    )
    client.post(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"username": "reader", "password": "reader-pass", "role": "user", "permission": "read_only"}
    )

    writer_token = _token_for(client, "writer", "writer-pass")
    create = client.post(
        "/pois/",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"latitude": 0.0, "longitude": 0.0},
    )
    poi_id = create.json()["id"]

    other_token = _token_for(client, "admin", "admin1234")
    # Create another user via login - use reader who shouldn't delete writer's poi
    reader_token = _token_for(client, "reader", "reader-pass")
    response = client.delete(
        f"/pois/{poi_id}",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 403

    admin_delete = client.delete(
        f"/pois/{poi_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert admin_delete.status_code == 204


def test_admin_can_manage_users(client: TestClient):
    admin_token = _token_for(client, "admin", "admin1234")
    headers = {"Authorization": f"Bearer {admin_token}"}
    create = client.post(
        "/users/",
        headers=headers,
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
        headers=headers,
        json={"permission": "read_write"},
    )
    assert patch.status_code == 200
    assert patch.json()["permission"] == "read_write"

    delete = client.delete(f"/users/{user_id}", headers=headers)
    assert delete.status_code == 204
