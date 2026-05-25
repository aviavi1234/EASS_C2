from fastapi.testclient import TestClient

from backend.conftest import auth_headers, create_poi, create_user, login


def test_read_only_can_list_and_read_pois(client: TestClient, admin_headers):
    poi = create_poi(client, admin_headers)
    create_user(client, admin_headers, "viewer", "viewer-pass", permission="read_only")
    token = login(client, "viewer", "viewer-pass")
    headers = auth_headers(token)

    assert client.get("/pois/", headers=headers).status_code == 200
    assert client.get(f"/pois/{poi['id']}", headers=headers).status_code == 200


def test_read_only_cannot_update_or_delete_poi(client: TestClient, admin_headers):
    poi = create_poi(client, admin_headers)
    create_user(client, admin_headers, "viewer2", "viewer2-pass", permission="read_only")
    headers = auth_headers(login(client, "viewer2", "viewer2-pass"))

    assert client.patch(
        f"/pois/{poi['id']}", headers=headers, json={"description": "nope"}
    ).status_code == 403
    assert client.delete(f"/pois/{poi['id']}", headers=headers).status_code == 403


def test_read_write_can_modify_own_poi(client: TestClient, admin_headers):
    create_user(client, admin_headers, "owner", "owner-pass", permission="read_write")
    headers = auth_headers(login(client, "owner", "owner-pass"))
    poi = create_poi(client, headers, description="mine")

    update = client.patch(
        f"/pois/{poi['id']}", headers=headers, json={"description": "updated mine"}
    )
    assert update.status_code == 200
    assert update.json()["description"] == "updated mine"

    delete = client.delete(f"/pois/{poi['id']}", headers=headers)
    assert delete.status_code == 204


def test_read_write_cannot_modify_other_users_poi(client: TestClient, admin_headers):
    create_user(client, admin_headers, "owner2", "owner2-pass", permission="read_write")
    create_user(client, admin_headers, "other", "other-pass", permission="read_write")

    owner_headers = auth_headers(login(client, "owner2", "owner2-pass"))
    other_headers = auth_headers(login(client, "other", "other-pass"))

    poi = create_poi(client, owner_headers, description="owned by owner2")

    assert client.patch(
        f"/pois/{poi['id']}", headers=other_headers, json={"description": "stolen"}
    ).status_code == 403
    assert client.delete(f"/pois/{poi['id']}", headers=other_headers).status_code == 403


def test_admin_can_modify_any_poi(client: TestClient, admin_headers):
    create_user(client, admin_headers, "lonely", "lonely-pass", permission="read_write")
    user_headers = auth_headers(login(client, "lonely", "lonely-pass"))
    poi = create_poi(client, user_headers, description="user poi")

    update = client.patch(
        f"/pois/{poi['id']}", headers=admin_headers, json={"description": "admin edit"}
    )
    assert update.status_code == 200
    assert update.json()["description"] == "admin edit"

    assert client.delete(f"/pois/{poi['id']}", headers=admin_headers).status_code == 204


def test_unknown_poi_type_rejected(client: TestClient, admin_headers):
    response = client.post(
        "/pois/",
        headers=admin_headers,
        json={"latitude": 1.0, "longitude": 2.0, "poi_type": "Submarine"},
    )
    assert response.status_code == 400
    assert "Unknown poi_type" in response.json()["detail"]
