"""On-disk storage for uploaded POI type marker icons."""

import re
from pathlib import Path

from backend.paths import POI_ICONS_DIR, USER_ICONS_DIR, ensure_data_dirs

ALLOWED_ICON_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def icons_directory() -> Path:
    ensure_data_dirs()
    return POI_ICONS_DIR


def user_icons_directory() -> Path:
    ensure_data_dirs()
    return USER_ICONS_DIR


def safe_icon_basename(name: str) -> bool:
    return bool(name) and bool(re.fullmatch(r"[A-Za-z0-9._-]+", name))
