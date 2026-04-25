"""Windows-Backend: Monitor-Erkennung via Win32 + Chroma-Key-Transparenz."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import tkinter as tk
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
    """Work-Area des Monitors, auf dem das fokussierte Fenster liegt."""
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


def configure_overlay_window(root: tk.Tk, panel_color: str, chroma_color: str) -> bool:
    """Konfiguriert das Overlay-Root-Window plattformspezifisch.

    Windows: Chroma-Key-Trick — das Root-Window wird mit `chroma_color` gefuellt;
    Pixel exakt dieser Farbe rendert Windows als transparent. Das innere
    runde CTkFrame schwebt dadurch frei auf dem Desktop.

    Returns True wenn der Chroma-Key aktiv ist (Caller laesst den Outer-Pad).
    Returns False als Fallback (Caller faerbt das Root in panel_color um).
    """
    try:
        # CTk-Root: fg_color setzen
        root.configure(fg_color=chroma_color)  # type: ignore[call-arg]
    except Exception:
        pass
    try:
        root.wm_attributes("-transparentcolor", chroma_color)
        return True
    except tk.TclError:
        # Falls der Treiber das nicht unterstuetzt: Fallback auf Panel-BG.
        try:
            root.configure(fg_color=panel_color)  # type: ignore[call-arg]
        except Exception:
            pass
        return False
