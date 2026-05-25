"""Local demo walkthrough for graders (EX3)."""

import json
import os
import subprocess
import sys
import time

import httpx

API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def wait_for_api(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = httpx.get(f"{API}/health", timeout=2.0)
            if response.status_code == 200:
                print("[demo] API healthy")
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError(f"API not reachable at {API}")


def login(username: str, password: str) -> str:
    response = httpx.post(
        f"{API}/auth/token",
        json={"username": username, "password": password},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> None:
    print("=== C2 EX3 Demo ===")
    print("Prerequisites:")
    print("  1) docker compose up -d --build   OR   python -m uvicorn backend.main:app --reload")
    print("  2) docker compose up -d worker     OR   python -m worker.main")
    print("  3) streamlit run frontend/streamlit/app.py")
    print()

    wait_for_api()

    admin_token = login("admin", "admin1234")
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = httpx.post(
        f"{API}/pois/",
        headers=headers,
        json={
            "latitude": 32.1,
            "longitude": 34.8,
            "poi_type": "Tank",
            "description": "demo hostile armor",
        },
        timeout=10.0,
    )
    create_resp.raise_for_status()
    poi = create_resp.json()
    print(f"[demo] Created POI #{poi['id']}")

    filtered = httpx.get(
        f"{API}/pois/",
        headers=headers,
        params={"poi_type": "Tank", "description_contains": "demo"},
        timeout=10.0,
    )
    filtered.raise_for_status()
    print(f"[demo] Filtered POIs: {len(filtered.json())}")

    digest = httpx.get(f"{API}/pois/digest/weekly", headers=headers, timeout=10.0)
    digest.raise_for_status()
    print("[demo] Weekly digest:")
    print(json.dumps(digest.json(), indent=2))

    refresh_cmd = [
        sys.executable,
        "-m",
        "scripts.refresh",
        "--api-base",
        API,
        "--run-id",
        "demo",
        "--concurrency",
        "3",
    ]
    print("[demo] Running refresh orchestrator...")
    result = subprocess.run(refresh_cmd, check=False)
    if result.returncode != 0:
        print("[demo] Refresh orchestrator failed (is Redis running?)")

    print("[demo] Done. Open Streamlit dashboard to export CSV and review metrics.")


if __name__ == "__main__":
    main()
