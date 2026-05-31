# EX3 Architecture Notes

## Services (monorepo)


| Service                     | Role                                       | Entry                                         |
| --------------------------- | ------------------------------------------ | --------------------------------------------- |
| `backend` (FastAPI)         | POI API, auth, digest, health              | `python -m uvicorn backend.main:app --reload` |
| SQLite via SQLModel         | Persistence (`data/database/`)             | auto on API start                             |
| `frontend/nicegui/main.py`  | Operations map UI                          | `python -m frontend.nicegui.main`             |
| `frontend/streamlit/app.py` | Operator UI                                | `streamlit run frontend/streamlit/app.py`     |
| `worker`                    | Redis queue consumer → refresh priorities  | `python -m worker.main`                       |
| `scripts/refresh.py`        | Async orchestrator (enqueue + idempotency) | `python -m scripts.refresh --run-id local`    |


See also: [docs/compose.md](compose.md)

## Orchestration

```text
Streamlit ──HTTP──► FastAPI API ──SQL──► SQLite
scripts/refresh ──enqueue──► Redis ◄──BLPOP── worker ──HTTP──► API /pois/{id}/refresh
```

Launch with:

```bash
docker compose up -d --build
python -m scripts.refresh --run-id ex3-demo --concurrency 5
docker compose logs -f worker
```

## Session 09 – Refresh trace excerpt

After `docker compose up -d --build` and `python -m scripts.refresh --run-id ex3-demo`:

```text
redis-cli MONITOR
1730000001.123456 [0 172.18.0.3:54321] "GET" "refresh:run:ex3-demo:poi:1"
1730000002.234567 [0 172.18.0.3:54321] "RPUSH" "refresh:queue" "{\"poi_id\": 1, \"idempotency_key\": \"refresh:run:ex3-demo:poi:1\", \"run_id\": \"ex3-demo\"}"
1730000003.345678 [0 172.18.0.4:54322] "BLPOP" "refresh:queue" "5"
1730000004.456789 [0 172.18.0.4:54322] "SET" "refresh:run:ex3-demo:poi:1" "1" "EX" "3600"
```

Worker logs (representative):

```text
2026-05-23 10:15:01 INFO refreshed poi_id=1 score=80.0
2026-05-23 10:15:02 INFO skip poi_id=1 (idempotent)
```

Automated coverage: `backend/test_refresh.py` includes `pytest.mark.anyio` orchestrator test.

## Session 11 – Security baseline

- Passwords stored with bcrypt (`passlib`).
- JWT bearer auth on user routes; roles: `user` (read_only or read_write) < `admin`.
- `POST`/`PATCH`/`DELETE` POIs require **read_write** permission or **admin**; users may only modify/delete **their own** POIs unless admin.
- `POST /pois/{id}/refresh` uses `SERVICE_API_KEY` bearer (worker only).
- Tests fail when a token is expired or missing scope (`backend/test_auth.py`).

### JWT secret rotation (local)

1. Set new secret: `set JWT_SECRET=new-secret-...` (Windows) or `export JWT_SECRET=...` (Unix)
2. Restart API/worker: `docker compose up -d --build`
3. Re-login all clients to obtain fresh tokens.
4. Old tokens fail with `401 Token expired or invalid`.

Default demo users (seeded on startup):


| User  | Password  | Role  |
| ----- | --------- | ----- |
| admin | admin1234 | admin |


## Enhancement

- **Searchable catalog filters** on `GET /pois/` (`poi_type`, `description_contains`).
- **Weekly digest** at `GET /pois/digest/weekly` (SQL aggregation for last 7 days).

