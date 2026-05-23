"""Use an isolated SQLite file for tests (before any ``backend.database`` import)."""

from __future__ import annotations

import os
import tempfile

_fd, _TEST_DB_PATH = tempfile.mkstemp(suffix="_c2_test.db")
os.close(_fd)
os.environ["C2_DB_FILE"] = _TEST_DB_PATH
