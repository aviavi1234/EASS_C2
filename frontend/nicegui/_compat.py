"""Python 3.14 compatibility for NiceGUI's vbuild dependency."""

from __future__ import annotations

import importlib.util
import pkgutil

if not hasattr(pkgutil, "find_loader"):

    def find_loader(name: str):
        spec = importlib.util.find_spec(name)
        return spec.loader if spec else None

    pkgutil.find_loader = find_loader  # type: ignore[attr-defined]
