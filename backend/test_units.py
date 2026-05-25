from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.conftest import auth_headers, create_user, login, png_upload
from backend.database import db
from backend.models import User


def test_user_can_update_unit_settings(client: TestClient, admin_headers):
    user = create_user(client, admin_headers, "unituser", "unituser-pass", permission="read_write")
    headers = auth_headers(login(client, "unituser", "unituser-pass"))

    patch = client.patch(
        f"/users/{user['id']}",
        headers=headers,
        json={
            "unit_name": "Bravo",
            "unit_type": "Infentry",
            "unit_description": "Mobile infantry",
            "unit_lat": 31.5,
            "unit_lng": 34.2,
            "show_location": True,
        },
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["unit_name"] == "Bravo"
    assert body["unit_type"] == "Infentry"
    assert body["show_location"] is True


def test_ping_updates_last_online(client: TestClient, admin_headers):
    users = client.get("/users/", headers=admin_headers).json()
    admin_id = next(u["id"] for u in users if u["username"] == "admin")

    client.patch(
        f"/users/{admin_id}",
        headers=admin_headers,
        json={"show_location": True},
    )

    ping = client.post("/users/me/ping", headers=admin_headers)
    assert ping.status_code == 200
    assert ping.json() == {"status": "ok"}

    refreshed = client.get("/users/", headers=admin_headers).json()
    admin_row = next(u for u in refreshed if u["username"] == "admin")
    assert admin_row["unit_last_online"] is not None


def test_units_list_shows_only_recent_online_with_location(client: TestClient, admin_headers):
    visible = create_user(client, admin_headers, "visible", "visible-pass", permission="read_write")
    hidden = create_user(client, admin_headers, "hidden", "hidden-pass", permission="read_write")

    visible_headers = auth_headers(login(client, "visible", "visible-pass"))
    hidden_headers = auth_headers(login(client, "hidden", "hidden-pass"))

    client.patch(
        f"/users/{visible['id']}",
        headers=visible_headers,
        json={
            "show_location": True,
            "unit_lat": 32.0,
            "unit_lng": 34.0,
            "unit_name": "Visible Unit",
        },
    )
    client.patch(
        f"/users/{hidden['id']}",
        headers=hidden_headers,
        json={"show_location": False, "unit_lat": 33.0, "unit_lng": 35.0},
    )
    client.post("/users/me/ping", headers=visible_headers)

    units = client.get("/units/", headers=admin_headers)
    assert units.status_code == 200
    names = {u["username"] for u in units.json()}
    assert "visible" in names
    assert "hidden" not in names


def test_offline_removes_unit_from_map(client: TestClient, admin_headers):
    user = create_user(client, admin_headers, "gone", "gone-pass", permission="read_write")
    headers = auth_headers(login(client, "gone", "gone-pass"))

    client.patch(
        f"/users/{user['id']}",
        headers=headers,
        json={"show_location": True, "unit_lat": 32.0, "unit_lng": 34.0},
    )
    client.post("/users/me/ping", headers=headers)

    assert any(u["username"] == "gone" for u in client.get("/units/", headers=admin_headers).json())

    offline = client.post("/users/me/offline", headers=headers)
    assert offline.status_code == 200

    units = client.get("/units/", headers=admin_headers).json()
    assert all(u["username"] != "gone" for u in units)


def test_stale_unit_not_listed(client: TestClient, admin_headers):
    stale = create_user(client, admin_headers, "stale", "stale-pass", permission="read_write")
    stale_headers = auth_headers(login(client, "stale", "stale-pass"))

    client.patch(
        f"/users/{stale['id']}",
        headers=stale_headers,
        json={"show_location": True, "unit_lat": 30.0, "unit_lng": 31.0},
    )

    with Session(db.engine) as session:
        user = session.get(User, stale["id"])
        user.unit_last_online = datetime.now(timezone.utc) - timedelta(seconds=120)
        session.add(user)
        session.commit()

    units = client.get("/units/", headers=admin_headers).json()
    assert all(u["username"] != "stale" for u in units)


def test_user_unit_icon_upload_and_delete(client: TestClient, admin_headers):
    user = create_user(client, admin_headers, "iconuser", "iconuser-pass", permission="read_write")
    headers = auth_headers(login(client, "iconuser", "iconuser-pass"))

    upload = client.post(
        f"/users/{user['id']}/icon",
        headers=headers,
        files={"file": png_upload()},
    )
    assert upload.status_code == 200
    assert upload.json()["unit_icon_url"] is not None

    icon_name = upload.json()["unit_icon_url"].split("/")[-1]
    assert client.get(f"/users/icons/{icon_name}").status_code == 200

    deleted = client.delete(f"/users/{user['id']}/icon", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["unit_icon_url"] is None


def test_user_cannot_upload_icon_for_other_user(client: TestClient, admin_headers):
    owner = create_user(client, admin_headers, "ownericon", "ownericon-pass", permission="read_write")
    other = create_user(client, admin_headers, "othericon", "othericon-pass", permission="read_write")
    other_headers = auth_headers(login(client, "othericon", "othericon-pass"))

    response = client.post(
        f"/users/{owner['id']}/icon",
        headers=other_headers,
        files={"file": png_upload()},
    )
    assert response.status_code == 403
