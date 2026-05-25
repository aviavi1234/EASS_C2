# Compose runbook — EX3 local stack

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- Python 3.10+ for local pytest (optional)

## Launch the stack

From the repository root:

```bash
docker compose up -d --build
```

This starts:

| Service | Role | URL / port |
|---------|------|------------|
| `api` | FastAPI backend + SQLite | http://127.0.0.1:8000 |
| `redis` | Refresh job queue | localhost:6379 |
| `worker` | Consumes queue → `POST /pois/{id}/refresh` | (background) |

Persistent data is mounted at `./data` (database, uploaded icons).

## Verify health

```bash
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}`

## Verify rate-limit headers

```bash
curl -i http://127.0.0.1:8000/poi-types/ -H "Authorization: Bearer <token>"
```

Look for:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`

(`/health`, `/users/me/ping`, and `/pois/{id}/refresh` are exempt from rate limiting.)

## Run the async refresh pipeline

1. Create at least one POI (via map GUI, Streamlit, or API).
2. Enqueue refresh jobs:

```bash
python -m scripts.refresh --run-id local --concurrency 5
```

3. Watch worker logs:

```bash
docker compose logs -f worker
```

4. Optional Redis trace:

```bash
docker compose exec redis redis-cli MONITOR
```

## Run tests locally

```bash
uv sync --extra dev
uv run python -m pytest backend frontend -svv
```

Or with `venv` + `pip`:

```bash
pip install -r requirements.txt -r requirements/dev.txt
python -m pytest backend frontend -svv
```

Async refresh orchestrator coverage includes `backend/test_refresh.py` (`pytest.mark.anyio`).
Demo script auth regression: `backend/test_demo.py`.

## CI (GitHub Actions)

On every push/PR, `.github/workflows/ci.yml` installs dependencies and runs:

```bash
python -m pytest backend frontend -svv
```

No Docker services are required for CI — tests use an isolated temp SQLite database.

## Optional — Schemathesis (API contract fuzzing)

With the Compose stack (or uvicorn) running and a valid JWT:

```bash
pip install schemathesis
schemathesis run http://127.0.0.1:8000/openapi.json \
  --checks all \
  --header "Authorization: Bearer <token>"
```

Obtain a token via `POST /auth/token` with seeded credentials (`admin` / `admin1234`). Schemathesis is optional locally; pytest is the required automated gate.

## Stop the stack

```bash
docker compose down
```

## Troubleshooting

- **Worker cannot reach API:** ensure `API_BASE_URL=http://api:8000` inside Compose (already set in `compose.yaml`).
- **401 on refresh:** worker and API must share `SERVICE_API_KEY` (default `dev-service-key`).
- **Empty queue:** run `python -m scripts.refresh --run-id local` after POIs exist.
- **Database reset:** stop Compose, delete `data/database/c2_database.db`, restart (seed runs on API startup).
