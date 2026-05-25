"""Shared pytest fixtures for backend API tests."""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_fd, _TEST_DB_PATH = tempfile.mkstemp(suffix="_c2_test.db")
os.close(_fd)
os.environ["C2_DB_FILE"] = _TEST_DB_PATH

from backend.database import db  # noqa: E402
from backend.main import app  # noqa: E402

MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


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


@pytest.fixture
def admin_token(client: TestClient) -> str:
    return login(client, "admin", "admin1234")


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    return auth_headers(admin_token)


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/token",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def create_user(
    client: TestClient,
    admin_headers: dict[str, str],
    username: str,
    password: str,
    *,
    permission: str = "read_only",
    role: str = "user",
) -> dict:
    response = client.post(
        "/users/",
        headers=admin_headers,
        json={
            "username": username,
            "password": password,
            "role": role,
            "permission": permission,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_poi(
    client: TestClient,
    headers: dict[str, str],
    *,
    latitude: float = 32.0,
    longitude: float = 34.0,
    poi_type: str = "Tank",
    description: str = "test poi",
) -> dict:
    response = client.post(
        "/pois/",
        headers=headers,
        json={
            "latitude": latitude,
            "longitude": longitude,
            "poi_type": poi_type,
            "description": description,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def png_upload(name: str = "icon.png"):
    return (name, io.BytesIO(MINIMAL_PNG), "image/png")
