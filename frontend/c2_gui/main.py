"""Backward-compatible entry point (use frontend.nicegui.main instead)."""

from frontend.nicegui.main import main

if __name__ in {"__main__", "__mp_main__"}:
    main()
