"""Plattform-Abstraktion: Monitor-Geometrie + Overlay-Window-Setup.

Das aufrufende Modul (`overlay.py`) bekommt eine einheitliche API; die
plattformspezifischen Implementierungen liegen in `_windows.py` / `_linux.py`.
"""
from __future__ import annotations

import sys

if sys.platform == "win32":
    from ._windows import (
        Rect,
        active_window_workarea,
        configure_overlay_window,
    )
elif sys.platform.startswith("linux"):
    from ._linux import (
        Rect,
        active_window_workarea,
        configure_overlay_window,
    )
else:
    raise RuntimeError(f"Plattform nicht unterstuetzt: {sys.platform}")

__all__ = ["Rect", "active_window_workarea", "configure_overlay_window"]
