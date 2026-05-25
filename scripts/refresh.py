"""Async orchestrator: enqueue POI refresh jobs with Redis-backed idempotency."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import httpx
import redis

from backend.config import get_settings
from backend.refresh_queue import REFRESH_QUEUE, idempotency_key, job_payload


async def _login(api_base: str, username: str, password: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{api_base.rstrip('/')}/auth/token",
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def _fetch_poi_ids(api_base: str, token: str) -> list[int]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{api_base.rstrip('/')}/pois/",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return [int(poi["id"]) for poi in response.json()]


def _enqueue_one(
    redis_client: redis.Redis,
    run_id: str,
    poi_id: int,
) -> str:
    key = idempotency_key(run_id, poi_id)
    if redis_client.get(key):
        return "skipped"
    redis_client.rpush(REFRESH_QUEUE, job_payload(run_id, poi_id))
    return "enqueued"


async def run_refresh(
    *,
    api_base: str,
    run_id: str,
    concurrency: int,
    username: str,
    password: str,
    redis_url: str | None = None,
) -> dict[str, int]:
    settings = get_settings()
    redis_url = redis_url or settings.redis_url
    redis_client = redis.from_url(redis_url, decode_responses=True)

    token = await _login(api_base, username, password)
    poi_ids = await _fetch_poi_ids(api_base, token)
    if not poi_ids:
        return {"enqueued": 0, "skipped": 0, "total": 0}

    semaphore = asyncio.Semaphore(max(1, concurrency))
    counts = {"enqueued": 0, "skipped": 0, "total": len(poi_ids)}

    async def _worker(poi_id: int) -> None:
        for attempt in range(3):
            try:
                async with semaphore:
                    result = await asyncio.to_thread(
                        _enqueue_one, redis_client, run_id, poi_id
                    )
                counts[result] += 1
                return
            except redis.RedisError:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))

    await asyncio.gather(*[_worker(poi_id) for poi_id in poi_ids])
    return counts


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Enqueue async POI refresh jobs")
    parser.add_argument("--api-base", default=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--run-id", required=True, help="Unique idempotency scope for this run")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--username", default=os.getenv("C2_ADMIN_USER", "admin"))
    parser.add_argument("--password", default=os.getenv("C2_ADMIN_PASSWORD", "admin1234"))
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL"))
    args = parser.parse_args(argv)

    try:
        summary = asyncio.run(
            run_refresh(
                api_base=args.api_base,
                run_id=args.run_id,
                concurrency=args.concurrency,
                username=args.username,
                password=args.password,
                redis_url=args.redis_url,
            )
        )
    except (httpx.HTTPError, redis.RedisError) as exc:
        print(f"[refresh] failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        "[refresh] run_id=%s total=%s enqueued=%s skipped=%s"
        % (args.run_id, summary["total"], summary["enqueued"], summary["skipped"])
    )


if __name__ == "__main__":
    main()
