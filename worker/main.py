"""Background worker: consumes Redis refresh jobs and calls the API."""

from __future__ import annotations

import logging
import os
import sys
import time

import httpx
import redis

from backend.config import get_settings
from backend.refresh_queue import REFRESH_QUEUE, parse_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("worker")


def process_job(
    *,
    api_base: str,
    service_key: str,
    redis_client: redis.Redis,
    raw_job: str,
    idempotency_ttl: int,
    max_retries: int = 3,
) -> None:
    job = parse_job(raw_job)
    poi_id = job["poi_id"]
    idem_key = job["idempotency_key"]

    if redis_client.get(idem_key):
        logger.info("skip poi_id=%s (idempotent)", poi_id)
        return

    url = f"{api_base.rstrip('/')}/pois/{poi_id}/refresh"
    headers = {"Authorization": f"Bearer {service_key}"}

    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.post(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            score = response.json().get("priority_score")
            redis_client.set(idem_key, "1", ex=idempotency_ttl)
            logger.info("refreshed poi_id=%s score=%s", poi_id, score)
            return
        except httpx.HTTPError as exc:
            logger.warning(
                "refresh failed poi_id=%s attempt=%s/%s: %s",
                poi_id,
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                time.sleep(0.5 * attempt)


def main() -> None:
    settings = get_settings()
    api_base = os.getenv("API_BASE_URL", settings.api_base_url).rstrip("/")
    service_key = os.getenv("SERVICE_API_KEY", settings.service_api_key)

    logger.info("Worker starting (api=%s, redis=%s)", api_base, settings.redis_url)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    while True:
        item = redis_client.blpop(REFRESH_QUEUE, timeout=5)
        if not item:
            continue
        _, raw_job = item
        try:
            process_job(
                api_base=api_base,
                service_key=service_key,
                redis_client=redis_client,
                raw_job=raw_job,
                idempotency_ttl=settings.refresh_idempotency_ttl_seconds,
            )
        except Exception as exc:
            logger.exception("Unhandled job error: %s", exc)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
