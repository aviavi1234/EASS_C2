from fastapi.testclient import TestClient

from backend.conftest import auth_headers, create_user, login


def test_list_users_admin_only(client: TestClient, admin_headers):
    create_user(client, admin_headers, "plain", "plain-pass")
    user_headers = auth_headers(login(client, "plain", "plain-pass"))

    assert client.get("/users/", headers=admin_headers).status_code == 200
    assert client.get("/users/", headers=user_headers).status_code == 403


def test_user_can_update_own_profile_not_others(client: TestClient, admin_headers):
    user_a = create_user(client, admin_headers, "usera", "usera-pass")
    create_user(client, admin_headers, "userb", "userb-pass")

    a_headers = auth_headers(login(client, "usera", "usera-pass"))
    b_headers = auth_headers(login(client, "userb", "userb-pass"))

    own = client.patch(
        f"/users/{user_a['id']}",
        headers=a_headers,
        json={"unit_name": "Unit A"},
    )
    assert own.status_code == 200
    assert own.json()["unit_name"] == "Unit A"

    other = client.patch(
        f"/users/{user_a['id']}",
        headers=b_headers,
        json={"unit_name": "Hacked"},
    )
    assert other.status_code == 403


def test_user_cannot_change_permission(client: TestClient, admin_headers):
    user = create_user(client, admin_headers, "permuser", "permuser-pass", permission="read_only")
    headers = auth_headers(login(client, "permuser", "permuser-pass"))

    response = client.patch(
        f"/users/{user['id']}",
        headers=headers,
        json={"permission": "read_write"},
    )
    assert response.status_code == 403


def test_admin_can_change_user_permission(client: TestClient, admin_headers):
    user = create_user(client, admin_headers, "promoted", "promoted-pass", permission="read_only")

    patch = client.patch(
        f"/users/{user['id']}",
        headers=admin_headers,
        json={"permission": "read_write"},
    )
    assert patch.status_code == 200
    assert patch.json()["permission"] == "read_write"


def test_admin_cannot_delete_self(client: TestClient, admin_headers):
    users = client.get("/users/", headers=admin_headers).json()
    admin_id = next(u["id"] for u in users if u["username"] == "admin")
    response = client.delete(f"/users/{admin_id}", headers=admin_headers)
    assert response.status_code == 400


def test_duplicate_username_rejected(client: TestClient, admin_headers):
    create_user(client, admin_headers, "dup", "dup-pass")
    response = client.post(
        "/users/",
        headers=admin_headers,
        json={"username": "dup", "password": "other-pass", "role": "user", "permission": "read_only"},
    )
    assert response.status_code == 409
