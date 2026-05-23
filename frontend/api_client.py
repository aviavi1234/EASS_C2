"""Shared HTTP client for frontends talking to the C2 API."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


class C2Client:
    def __init__(self, api_base: str = DEFAULT_API_BASE, token: str | None = None):
        self.api_base = api_base.rstrip("/")
        self.token = token

    def _headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def login(self, username: str, password: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.api_base}/auth/token",
            json={"username": username, "password": password},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data

    def get_health(self) -> dict[str, Any]:
        response = httpx.get(f"{self.api_base}/health", timeout=5)
        response.raise_for_status()
        return response.json()

    def fetch_pois(self) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.api_base}/pois/", headers=self._headers(), timeout=10
        )
        response.raise_for_status()
        return response.json()

    def create_poi(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.api_base}/pois/",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def update_poi(self, poi_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.patch(
            f"{self.api_base}/pois/{poi_id}",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def delete_poi(self, poi_id: int) -> None:
        response = httpx.delete(
            f"{self.api_base}/pois/{poi_id}",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()

    def fetch_users(self) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.api_base}/users/", headers=self._headers(), timeout=10
        )
        response.raise_for_status()
        return response.json()

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.api_base}/users/",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def patch_user(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.patch(
            f"{self.api_base}/users/{user_id}",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def delete_user(self, user_id: int) -> None:
        response = httpx.delete(
            f"{self.api_base}/users/{user_id}",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()

    def fetch_poi_types(self) -> list[dict[str, Any]]:
        response = httpx.get(
            f"{self.api_base}/poi-types/",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def create_poi_type(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.api_base}/poi-types/",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def update_poi_type(self, type_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.patch(
            f"{self.api_base}/poi-types/{type_id}",
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def delete_poi_type(self, type_id: int) -> None:
        response = httpx.delete(
            f"{self.api_base}/poi-types/{type_id}",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()

    def upload_poi_type_icon(
        self, type_id: int, content: bytes, filename: str
    ) -> dict[str, Any]:
        files = {"file": (filename, content)}
        response = httpx.post(
            f"{self.api_base}/poi-types/{type_id}/icon",
            headers=self._headers(),
            files=files,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

