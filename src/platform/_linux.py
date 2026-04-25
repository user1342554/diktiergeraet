"""Linux-Backend (X11): Monitor-Erkennung via screeninfo + flaches Pill ohne Chroma-Key.

Tk's `-transparentcolor` ist Windows-only — auf Linux faerben wir das Root in der
Panel-Farbe (bg = panel_color), die runde Inner-CTkFrame verschwindet visuell in der
gleichen Flaeche und das Pill wirkt wie ein flaches dunkles Rechteck.
"""
from __future__ import annotations

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


# Cinnamon/MATE/XFCE-Default: Panel ist meist unten ~28-40px. 50px Padding deckt
# alle Faelle und vermeidet die Notwendigkeit von _NET_WORKAREA-Lookups via Xlib.
_BOTTOM_PANEL_PAD = 50


def _primary_workarea_fallback() -> Rect:
    """Letzter Fallback ohne screeninfo: Bildschirm aus Tk."""
    try:
        root = tk._default_root  # type: ignore[attr-defined]
        if root is None:
            root = tk.Tk()
            root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        return Rect(0, 0, w, h - _BOTTOM_PANEL_PAD)
    except Exception:
        return Rect(0, 0, 1920, 1080 - _BOTTOM_PANEL_PAD)


def active_window_workarea() -> Rect:
    """Liefert die Work-Area des Monitors unter dem Mauszeiger.

    Auf X11 ist „aktives Fenster" via Xlib erreichbar, aber teurer und
    abhaengig von zusaetzlichen Pakteten. Mauszeiger-Position ist ein
    pragmatischer Proxy: das Overlay erscheint dort, wo der Nutzer arbeitet.
    """
    try:
        from screeninfo import get_monitors  # type: ignore
    except Exception:
        return _primary_workarea_fallback()

    # Mauszeiger via Tk holen
    try:
        root = tk._default_root  # type: ignore[attr-defined]
        if root is None:
            root = tk.Tk()
            root.withdraw()
        px, py = root.winfo_pointerxy()
    except Exception:
        return _primary_workarea_fallback()

    monitors = list(get_monitors())
    if not monitors:
        return _primary_workarea_fallback()

    # Monitor unter dem Mauszeiger finden
    for m in monitors:
        if m.x <= px < m.x + m.width and m.y <= py < m.y + m.height:
            return Rect(m.x, m.y, m.x + m.width, m.y + m.height - _BOTTOM_PANEL_PAD)

    # Fallback: Primary
    primary = next((m for m in monitors if getattr(m, "is_primary", False)), monitors[0])
    return Rect(
        primary.x,
        primary.y,
        primary.x + primary.width,
        primary.y + primary.height - _BOTTOM_PANEL_PAD,
    )


def configure_overlay_window(root: tk.Tk, panel_color: str, chroma_color: str) -> bool:
    """Linux-Variante: kein Chroma-Key. Root in Panel-Farbe; Caller skipt den
    Outer-Padding und das Pill belegt die volle Window-Flaeche.

    Returns False, damit `overlay.py` den Chroma-Pfad ueberspringt.
    """
    try:
        root.configure(fg_color=panel_color)  # type: ignore[call-arg]
    except Exception:
        pass

    # Kein Taskbar-Eintrag, ueber allen Fenstern, wirkt wie ein OSD.
    try:
        root.wm_attributes("-type", "splash")
    except tk.TclError:
        pass

    # Optional: leichte Window-Alpha fuer einen Hauch Glaseffekt.
    # Cinnamon/Muffin unterstuetzt das; wenn nicht, wird's einfach ignoriert.
    try:
        root.wm_attributes("-alpha", 0.97)
    except tk.TclError:
        pass

    return False
