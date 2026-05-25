"""Redis queue helpers for async POI priority refresh (Session 09 / EX3)."""

from __future__ import annotations

import json

REFRESH_QUEUE = "refresh:queue"


def idempotency_key(run_id: str, poi_id: int) -> str:
    return f"refresh:run:{run_id}:poi:{poi_id}"


def job_payload(run_id: str, poi_id: int) -> str:
    return json.dumps(
        {
            "poi_id": poi_id,
            "idempotency_key": idempotency_key(run_id, poi_id),
            "run_id": run_id,
        }
    )


def parse_job(raw: str) -> dict:
    data = json.loads(raw)
    return {
        "poi_id": int(data["poi_id"]),
        "idempotency_key": str(data["idempotency_key"]),
        "run_id": str(data.get("run_id", "")),
    }
