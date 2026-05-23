"""On-disk storage for uploaded POI type marker icons."""

import re
from pathlib import Path

ALLOWED_ICON_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def icons_directory() -> Path:
    base = Path(__file__).resolve().parent / "Data" / "poi_icons"
    base.mkdir(parents=True, exist_ok=True)
    return base


def safe_icon_basename(name: str) -> bool:
    return bool(name) and bool(re.fullmatch(r"[A-Za-z0-9._-]+", name))
