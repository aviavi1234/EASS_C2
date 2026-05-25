from fastapi.testclient import TestClient

from backend.conftest import auth_headers, create_poi, create_user, login, png_upload


def test_list_poi_types_requires_auth(client: TestClient):
    assert client.get("/poi-types/").status_code == 401


def test_list_poi_types_includes_defaults(client: TestClient, admin_headers):
    response = client.get("/poi-types/", headers=admin_headers)
    assert response.status_code == 200
    labels = {row["label"] for row in response.json()}
    assert "Tank" in labels


def test_only_admin_can_create_poi_type(client: TestClient, admin_headers):
    create_user(client, admin_headers, "regular", "regular-pass", permission="read_write")
    user_headers = auth_headers(login(client, "regular", "regular-pass"))

    assert client.post(
        "/poi-types/",
        headers=user_headers,
        json={"label": "Artillery"},
    ).status_code == 403

    created = client.post(
        "/poi-types/",
        headers=admin_headers,
        json={"label": "Artillery"},
    )
    assert created.status_code == 201
    assert created.json()["label"] == "Artillery"


def test_admin_can_rename_poi_type_and_updates_pois(client: TestClient, admin_headers):
    created = client.post(
        "/poi-types/",
        headers=admin_headers,
        json={"label": "RenameMe"},
    )
    type_id = created.json()["id"]
    poi = create_poi(client, admin_headers, poi_type="RenameMe")

    patch = client.patch(
        f"/poi-types/{type_id}",
        headers=admin_headers,
        json={"label": "RenamedType"},
    )
    assert patch.status_code == 200

    refreshed = client.get(f"/pois/{poi['id']}", headers=admin_headers)
    assert refreshed.json()["poi_type"] == "RenamedType"


def test_cannot_delete_poi_type_in_use(client: TestClient, admin_headers):
    created = client.post(
        "/poi-types/",
        headers=admin_headers,
        json={"label": "InUseType"},
    )
    type_id = created.json()["id"]
    create_poi(client, admin_headers, poi_type="InUseType")

    response = client.delete(f"/poi-types/{type_id}", headers=admin_headers)
    assert response.status_code == 409


def test_admin_can_delete_unused_poi_type(client: TestClient, admin_headers):
    created = client.post(
        "/poi-types/",
        headers=admin_headers,
        json={"label": "UnusedType"},
    )
    type_id = created.json()["id"]
    assert client.delete(f"/poi-types/{type_id}", headers=admin_headers).status_code == 204


def test_poi_type_icon_upload_and_delete(client: TestClient, admin_headers):
    created = client.post(
        "/poi-types/",
        headers=admin_headers,
        json={"label": "IconType"},
    )
    type_id = created.json()["id"]

    upload = client.post(
        f"/poi-types/{type_id}/icon",
        headers=admin_headers,
        files={"file": png_upload()},
    )
    assert upload.status_code == 200
    assert upload.json()["icon_url"] is not None

    icon_name = upload.json()["icon_url"].split("/")[-1]
    assert client.get(f"/poi-types/icons/{icon_name}").status_code == 200

    deleted = client.delete(f"/poi-types/{type_id}/icon", headers=admin_headers)
    assert deleted.status_code == 200
    assert deleted.json()["icon_url"] is None
