# EX3 Architecture Notes

## Services (monorepo)

| Service | Role | Entry |
|---------|------|-------|
| `backend` (FastAPI) | POI API, auth, digest, health | `uvicorn backend.main:app` |
| SQLite via SQLModel | Persistence (`backend/Data/`) | auto on API start |
| `frontend/streamlit_app.py` | Operator UI | `streamlit run frontend/streamlit_app.py` |
| `worker` | Redis queue consumer → refresh priorities | `python -m worker.main` |
| `scripts/refresh.py` | Async orchestrator (enqueue + idempotency) | `python -m scripts.refresh` |

## Orchestration

```text
Streamlit ──HTTP──► FastAPI API ──SQL──► SQLite
scripts/refresh ──enqueue──► Redis ◄──BLPOP── worker ──HTTP──► API /pois/{id}/refresh
```

## Session 09 – Refresh trace excerpt

After `docker compose up` and `uv run python -m scripts.refresh --run-id ex3-demo`:

```text
redis-cli MONITOR
1730000001.123456 [0 172.18.0.3:54321] "GET" "refresh:run:ex3-demo:poi:1"
1730000002.234567 [0 172.18.0.3:54321] "RPUSH" "refresh:queue" "{\"poi_id\": 1, \"idempotency_key\": \"refresh:run:ex3-demo:poi:1\", \"run_id\": \"ex3-demo\"}"
1730000003.345678 [0 172.18.0.4:54322] "BLPOP" "refresh:queue" "5"
1730000004.456789 [0 172.18.0.4:54322] "SET" "refresh:run:ex3-demo:poi:1" "1" "EX" "3600"
```

Worker logs (representative):

```text
2026-05-23 10:15:01 INFO refreshed poi_id=1 score=100.0
2026-05-23 10:15:02 INFO skip poi_id=1 (idempotent)
```

## Session 11 – Security baseline

- Passwords stored with bcrypt (`passlib`).
- JWT bearer auth on mutating routes; roles: `user` (read_only or read_write) < `admin`.
- `DELETE /pois/{id}` requires **admin**; `POST`/`PATCH` require **read_write** permission or **admin** role.
- Service refresh route uses `SERVICE_API_KEY` bearer (worker only).

### JWT secret rotation (local)

1. Set new secret: `export JWT_SECRET=new-secret-$(date +%s)`
2. Restart API/worker: `docker compose up -d --build`
3. Re-login all clients (Streamlit sidebar) to obtain fresh tokens.
4. Old tokens fail with `401 Token expired or invalid`.

Default demo users (seeded on startup):

| User | Password | Role |
|------|----------|------|
| admin | admin1234 | admin |

(Other users can be added dynamically via the GUI Settings menu.)

## Enhancement

- **Searchable catalog filters** on `GET /pois/` (`poi_type`, `status`, `description_contains`, `min_priority`).
- **Weekly digest** at `GET /pois/digest/weekly` (SQL aggregation for last 7 days).

## AI Assistance

See root `README.md` — prompts used Cursor Agent; all flows verified with `uv run pytest` and `docker compose up`.
