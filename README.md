# Command & Control (C2) - POI Mapping Platform

This repository contains the full-stack microservices project for the Command & Control (C2) mapping platform.

**Domain Theme:** Military / Emergency Points of Interest (POI) tracking (Tanks, Infantry, Unknowns).

## Architecture & Services

The project consists of three cooperating local microservices:
1. **API (Backend):** FastAPI backend managing POIs, authentication, types, and settings. Backed by SQLite (via SQLModel).
2. **Redis & Worker:** Asynchronous background worker (`worker/main.py`) consuming tasks from a Redis queue, orchestrated by `scripts/refresh.py`.
3. **Interfaces (Frontend):** 
   - A highly responsive Leaflet map GUI built with **NiceGUI** (`frontend/c2_gui/main.py`).
   - A lightweight dashboard built with **Streamlit** (`frontend/streamlit_app.py`).

## Quickstart (Full Stack)

The simplest way to run the entire stack locally without configuration is via Docker Compose:

```bash
# Launch the API, Redis, and Background Worker
docker compose up -d --build

# Run the async orchestrator to trigger background priority refreshes
uv run python -m scripts.refresh --run-id local --concurrency 5

# Launch the primary Map GUI
uv run python -m frontend.c2_gui.main
```

*See `docs/runbooks/compose.md` and `docs/EX3-notes.md` for detailed orchestration logs, security rotation, and architectural traces.*

---

## Local Development Setup

If you prefer to run services manually outside of Docker using `uv`:

### 1. Create the `uv` environment & install dependencies

```bash
# Install uv if you don't have it (https://github.com/astral-sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies into a virtual environment
uv venv
uv pip install -r requirements.txt
```

### 2. Run the Backend API

```bash
uv run uvicorn backend.main:app --reload --port 8000
```
- API is available at: http://127.0.0.1:8000
- Interactive Swagger docs: http://127.0.0.1:8000/docs
- *Persistence:* An SQLite database is automatically generated at `backend/Data/c2_database.db`.

### 3. Run the Interfaces Side-by-Side

In a new terminal window, launch one of the interfaces:

**Option A: C2 Operations Map (NiceGUI)**
```bash
uv run python -m frontend.c2_gui.main
```
*(Opens automatically in browser, usually at http://localhost:8080)*

**Option B: Dashboard (Streamlit)**
```bash
uv run streamlit run frontend/streamlit_app.py
```
*(Opens at http://localhost:8501)*

---

## Testing & Quality

Tests are written using `pytest` and FastAPI's `TestClient`, covering happy paths, security, and idempotency.

```bash
# Run the full test suite
uv run pytest -svv
```

---

## Security & Authentication

The application enforces a firm security baseline:
- Credentials are mathematically hashed using `passlib/bcrypt`.
- API routes are protected using **JWT Bearer Auth**.
- **Role-Based Access Control (RBAC):**
  - **`user` (read_only):** Can view POIs.
  - **`user` (read_write):** Can view and create POIs. Can only edit/delete their own POIs.
  - **`admin`:** Can manage users, POI types, activity settings, and edit/delete ANY POI.

**Default Demo Account:**
- **Username:** `admin`
- **Password:** `admin1234`
*(Note: Initial setup is forced on the first login requiring password changes matching strict complexity rules).*

---

## Enhancements

This release includes the following thoughtful enhancements:
1. **Searchable Catalog Filters:** API supports sophisticated querying (`GET /pois/?poi_type=Tank&description_contains=hostile`).
2. **Weekly Digest Analytics:** An aggregated SQL-driven metric report endpoint (`GET /pois/digest/weekly`).
3. **Local User Settings:** UI customizations (activity tiers, date/time formats) are managed locally in browser storage per device.

## Walkthrough Demo Script

To help graders test the end-to-end integration (API, interfaces, and enhancements) without manual clicks:

```bash
# Ensure API, Redis, and Worker are running (docker compose up -d)
# Then run the automated demonstration
uv run python -m app.demo

# Or use the wrapper script
bash scripts/demo.sh
```
