"""Shared filesystem paths for runtime data (database, uploads, certs)."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("C2_DATA_DIR", REPO_ROOT / "data"))

DATABASE_DIR = DATA_DIR / "database"
POI_ICONS_DIR = DATA_DIR / "poi_icons"
USER_ICONS_DIR = DATA_DIR / "user_icons"
CERTS_DIR = DATA_DIR / "certs"

DEFAULT_DB_FILE = DATABASE_DIR / "c2_database.db"
DEFAULT_CERT_FILE = CERTS_DIR / "cert.pem"
DEFAULT_KEY_FILE = CERTS_DIR / "key.pem"


def ensure_data_dirs() -> None:
    for path in (DATABASE_DIR, POI_ICONS_DIR, USER_ICONS_DIR, CERTS_DIR):
        if path.exists() and not path.is_dir():
            raise FileExistsError(f"Expected directory but found file: {path}")
        path.mkdir(parents=True, exist_ok=True)
