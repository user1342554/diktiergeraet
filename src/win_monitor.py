"""Findet den Monitor, auf dem das aktive Fenster liegt (Windows only)."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from dataclasses import dataclass


@dataclass
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("rcMonitor", wt.RECT),
        ("rcWork", wt.RECT),
        ("dwFlags", wt.DWORD),
    ]


_MONITOR_DEFAULTTONEAREST = 2


def _primary_workarea_fallback() -> Rect:
    spi_rect = wt.RECT()
    # SPI_GETWORKAREA = 0x0030
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(spi_rect), 0)
    return Rect(spi_rect.left, spi_rect.top, spi_rect.right, spi_rect.bottom)


def active_window_workarea() -> Rect:
    """Liefert die Work-Area (ohne Taskleiste) des Monitors, auf dem
    das aktuell fokussierte Fenster liegt. Fallback: Primary-Monitor."""
    user32 = ctypes.windll.user32
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return _primary_workarea_fallback()
        hmon = user32.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
        if not hmon:
            return _primary_workarea_fallback()
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(_MONITORINFO)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return _primary_workarea_fallback()
        r = mi.rcWork
        return Rect(r.left, r.top, r.right, r.bottom)
    except Exception:
        return _primary_workarea_fallback()
