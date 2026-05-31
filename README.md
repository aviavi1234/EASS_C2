# Command & Control (C2) - POI Mapping Platform

This repository is a **computer-science course project** that follows an assignment series (**EX1 → EX2 → EX3**), building one product incrementally across three exercises.

**Domain Theme:** Military / Emergency Points of Interest (POI) tracking (Tanks, Infantry, Unknowns).

## Course exercises (EX1–EX3)


| Exercise | Focus                                     | Main locations                                                                                   |
| -------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **EX1**  | FastAPI backend, SQLite, pytest           | `backend/`, `scripts/init/seed.py`, `backend/test_*.py`                                          |
| **EX2**  | Streamlit dashboard                       | `frontend/streamlit/app.py`                                                                      |
| **EX3**  | Compose, Redis worker, JWT, async refresh | `compose.yaml`, `worker/`, `scripts/refresh.py`, `docs/EX3-notes.md`, `docs/compose.md` |


NiceGUI map UI (`frontend/nicegui/`) is an EX3 enhancement.

---

## Project Layout

```
backend/                 FastAPI application (API, auth, models, services)
worker/                  Redis queue consumer for async POI refresh
frontend/
  shared/                Shared HTTP client and UI helpers
  nicegui/               Primary map GUI (Leaflet + NiceGUI)
  streamlit/             Dashboard frontend (EX2)
scripts/
  init/                  Database seed and local HTTPS cert generation
  refresh.py             Async refresh orchestrator (EX3)
deploy/                  Dockerfile (used by compose)
docs/
  full-GUI-user-guide.md Screen-by-screen UI guide (with screenshots)
  EX3-notes.md           Architecture, security, refresh trace
  compose.md             Docker Compose runbook
  images/                UI screenshots
data/                    Runtime data (SQLite DB, icons, certs) — not committed
requirements/            Split dependency files by component
compose.yaml             Full stack: API, Streamlit, NiceGUI, Redis, worker
```

## Architecture & Services


| Service            | Role                                               |
| ------------------ | -------------------------------------------------- |
| **API (backend)**  | EX1 — FastAPI + SQLModel/SQLite                    |
| **Redis + worker** | EX3 — async priority refresh queue                 |
| **Streamlit**      | EX2 table dashboard — list, create, filter, export |
| **NiceGUI map**    | EX3 operations map UI                              |


---

## Quickstart (local Python)

> **Prefer Docker?** See [EX3 – Docker Compose stack](#ex3--docker-compose-stack) to run the API, Streamlit, NiceGUI map, Redis, and worker together with `docker compose up -d --build`.

Run from the **project root**. Do steps **1 → 2 → 3 → 4** in order; use a **new terminal** for each running service.

Use the venv Python directly — no shell activation script needed (avoids PowerShell execution-policy errors on Windows):


| OS            | Command prefix               |
| ------------- | ---------------------------- |
| Windows       | `venv\Scripts\python.exe -m` |
| Linux / macOS | `venv/bin/python -m`         |


The examples below use the venv Python from the table above.

### 1. Install dependencies (setup)

**Python 3.10+** (tested through 3.14).

```bash
# Windows
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements/dev.txt

# Linux / macOS
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt -r requirements/dev.txt
```

### 2. EX1 — Run the backend (terminal 1)

```bash
# Windows
venv\Scripts\python.exe -m uvicorn backend.main:app --reload

# Linux / macOS
venv/bin/python -m uvicorn backend.main:app --reload
```

- API: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Database: `data/database/c2_database.db` (auto-created)

The backend listens on port **8000**. EX2 and EX3 frontends run on **other ports** and talk to this API.

#### First login (new database)

When the database is **new**, any UI will ask you to sign in. Use:


| Field    | Value       |
| -------- | ----------- |
| Username | `admin`     |
| Password | `admin1234` |


On first login you must choose a new username and password (map GUI) or connect via the Streamlit sidebar (EX2).

### 3. EX2 — Run the Streamlit dashboard (terminal 2, optional)

```bash
# Windows
venv\Scripts\python.exe -m streamlit run frontend/streamlit/app.py

# Linux / macOS
venv/bin/python -m streamlit run frontend/streamlit/app.py
```

Opens at [http://127.0.0.1:8501](http://127.0.0.1:8501). In the sidebar, connect to the API with **admin** / **admin1234** on a new database (see above).

Table view: list POIs, create entries, filter, export CSV/JSON.

### 4. EX3 — Run the map GUI (terminal 3)

```bash
# Windows
venv\Scripts\python.exe -m frontend.nicegui.main

# Linux / macOS
venv/bin/python -m frontend.nicegui.main
```

Opens at [http://127.0.0.1:8081](http://127.0.0.1:8081). In **Settings → Unit location**, choose **Auto** to use GPS.

**Troubleshooting**:

> **• Port 8081 already in use** — pick any free port with `--port` (example uses `8090`; use whatever you like):
>
> ```bash
> # Windows — replace 8090 with your port
> venv\Scripts\python.exe -m frontend.nicegui.main --port 8090
>
> # Linux / macOS — replace 8090 with your port
> venv/bin/python -m frontend.nicegui.main --port 8090
> ```
>
> Opens at `http://127.0.0.1:<your-port>` (example: [http://127.0.0.1:8090](http://127.0.0.1:8090)).
>
> **• Enable GPS location** — GPS in the browser requires **HTTPS** when the map is opened over your LAN (e.g. from a phone at `https://YOUR_PC_IP:…`). Start the map with `**--https`** to enable it.
> `--port` is optional (as explained above, example `8090`):
>
> ```bash
> # Windows — replace 8090 with your port, or omit --port to use the default
> venv\Scripts\python.exe -m frontend.nicegui.main --https --port 8090
>
> # Linux / macOS — replace 8090 with your port, or omit --port to use the default
> venv/bin/python -m frontend.nicegui.main --https --port 8090
> ```
>
> Then on your phone (same Wi‑Fi as the PC):
>
> 1. Open `https://YOUR_PC_IP:<your-port>` (example: `https://192.168.0.117:8090`).
> 2. If the browser uses HTTP and fails, try `http://YOUR_PC_IP:<your-port + 1>` — example: port `8090` → try `http://…:8091` (redirects to HTTPS).
> 3. Accept the certificate warning (Advanced → Proceed).
> 4. Log in; leave **Advanced Server Settings → Server IP** as `**127.0.0.1`**.
> 5. Set **Unit location → Auto** for GPS.
>
> **Windows firewall** — if the phone cannot open the map on the same Wi‑Fi, run in Administrator PowerShell: `.\scripts\dev\open_firewall.ps1`

---

## Using the application

After you complete the [Quickstart (local Python)](#quickstart-local-python) or [Docker Compose stack](#ex3--docker-compose-stack), see **[docs/full-GUI-user-guide.md](docs/full-GUI-user-guide.md)** for a screen-by-screen guide to the NiceGUI map and Streamlit dashboard (login, map, settings, roles, and screenshots).

---

## EX3 – Docker Compose stack

Run the **entire application** in containers — API, both frontends, Redis, and the refresh worker — with one command. Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose plugin).

From the repository root:

```bash
docker compose up -d --build
```

### Services


| Service     | Role                                      | URL                                              |
| ----------- | ----------------------------------------- | ------------------------------------------------ |
| `api`       | FastAPI backend + SQLite                  | [http://127.0.0.1:8000](http://127.0.0.1:8000)   |
| `streamlit` | EX2 table dashboard                       | [http://127.0.0.1:8501](http://127.0.0.1:8501)   |
| `nicegui`   | EX3 operations map                        | [http://127.0.0.1:8081](http://127.0.0.1:8081)   |
| `redis`     | Refresh job queue                         | `localhost:6379`                                 |
| `worker`    | Async POI refresh (background)            | —                                                |


Persistent data (database, uploaded icons) is stored in `./data` via a volume mount.

### First login

On a **new database**, sign in with:


| Field    | Value       |
| -------- | ----------- |
| Username | `admin`     |
| Password | `admin1234` |


- **Streamlit** — use the sidebar **Connect** button (API URL is pre-filled).
- **NiceGUI** — log in on the home page (Advanced Server Settings default to the internal API host; no change needed).

Frontends reach the API at `http://api:8000` inside the Compose network.

### Verify the stack

```bash
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}`

Stop everything:

```bash
docker compose down
```

Detailed runbook (rate limits, refresh pipeline, troubleshooting): [docs/compose.md](docs/compose.md)

### Async POI refresh pipeline

EX3 adds a **background job queue** that recalculates POI **priority scores** in bulk without blocking the API or any UI. “Refresh” does not move POIs or fetch external data — it updates `priority_score` and `last_refreshed_at` in SQLite based on POI type (e.g. Tank → 80, Infantry → 60, Unknown → 20).

**Flow:**

```text
scripts/refresh  ──enqueue──►  Redis (refresh:queue)  ◄──BLPOP──  worker
                                                                    │
                                                                    ▼
                                                         POST /pois/{id}/refresh
                                                         (SERVICE_API_KEY)
                                                                    │
                                                                    ▼
                                                               SQLite
```

| Component | Role |
| --------- | ---- |
| `scripts/refresh.py` | Orchestrator — logs in, lists all POI IDs, pushes one job per POI onto Redis |
| `redis` | Holds the job queue and idempotency keys |
| `worker` | Pulls jobs, calls the refresh API endpoint, retries on failure |
| `POST /pois/{id}/refresh` | Service-key-only route; recomputes priority and timestamps the POI |

**Idempotency:** Each run uses a `--run-id` (e.g. `local`). Redis keys like `refresh:run:local:poi:7` ensure the same POI is not refreshed twice in the same run. Re-running with a **new** `run-id` refreshes everything again.

**Run it** (Compose must be up with POIs in the database):

```bash
# Windows
venv\Scripts\python.exe -m scripts.refresh --run-id local --concurrency 5

# Linux / macOS
venv/bin/python -m scripts.refresh --run-id local --concurrency 5

# Watch the worker process jobs:
docker compose logs -f worker
```

The orchestrator runs on your host (or in a venv); it needs reachability to Redis (`localhost:6379` when using Compose) and the API (`http://127.0.0.1:8000`). More detail: [docs/EX3-notes.md](docs/EX3-notes.md), [docs/compose.md](docs/compose.md).

---

## Initialize database manually (optional)

```bash
# Windows
venv\Scripts\python.exe -m scripts.init.seed

# Linux / macOS
venv/bin/python -m scripts.init.seed
```

Default admin: `admin` / `admin1234` (forced password change on first login).

---

## Testing

```bash
# Windows
venv\Scripts\python.exe -m pytest backend frontend -svv

# Linux / macOS
venv/bin/python -m pytest backend frontend -svv
```

Coverage includes authentication, RBAC, POI/unit CRUD, POI types, icons, database seeding, client-side settings helpers, and async refresh (`pytest.mark.anyio`). **63 tests** total.

---

## Security & Authentication

- Passwords hashed with **bcrypt** (`passlib`)
- **JWT Bearer** auth on user routes
- **RBAC:**
  - `user` (`read_only`): view POIs
  - `user` (`read_write`): create/edit/delete own POIs
  - `admin`: manage users, POI types, any POI
- **Service key** (`SERVICE_API_KEY`, default `dev-service-key`): worker refresh route only

See [docs/EX3-notes.md](docs/EX3-notes.md) for JWT rotation steps.

---

## Enhancements

1. **Searchable filters:** `GET /pois/?poi_type=Tank&description_contains=hostile`
2. **Weekly digest:** `GET /pois/digest/weekly`
3. **Friendly units:** user location sharing on the map
4. **Local UI settings:** activity tiers, date/time format (browser storage)

---

## AI Assistance

Cursor was used for scaffolding, tests, and documentation. All generated output was reviewed manually and verified with `pytest` and local runs against the API.