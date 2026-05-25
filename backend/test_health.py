from fastapi.testclient import TestClient


def test_health_no_auth_required(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
