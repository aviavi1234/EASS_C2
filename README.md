# C2 Platform Foundation

This repository is the initial foundation for a future **Command and Control (C2)** application.

At this stage, the project includes:
- a minimal backend API for managing POIs (Points of Interest)
- a simple Streamlit dashboard for quick interaction

The current scope is intentionally lightweight so it is easy to extend in future exercises and project phases.

## Current Project Structure

```text
EASS_HIT_C2/
├── backend/
│   ├── Data/                 # DB files (main + test) are created here
│   ├── __init__.py
│   ├── database.py           # Engine/session management
│   ├── main.py               # FastAPI routes
│   ├── models.py             # SQLModel models and schemas
│   └── test_main.py          # Backend tests
├── frontend/
│   └── streamlit_app.py      # Simple dashboard
├── requirements.txt
└── README.md
```

## Tech Stack (Current)

- FastAPI
- SQLModel + SQLite
- Streamlit
- pytest + FastAPI TestClient

## Setup

1. Use Python 3.10+
2. Create and activate a virtual environment
3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run Backend (Terminal 1)

From the repository root:

```bash
python -m uvicorn backend.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Main DB file is created automatically at `backend/Data/c2_database.db`.

## Run Dashboard (Terminal 2)

From the repository root:

```bash
python -m streamlit run frontend/streamlit_app.py
```

Dashboard URL: `http://localhost:8501`

## Run Tests

From the repository root:

```bash
python -m pytest -svv backend/test_main.py
```
