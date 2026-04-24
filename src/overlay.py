"""Kleines Always-On-Top Status-Fenster mit Audio-Spektrum-Visualizer (Tk)."""
from __future__ import annotations

import tkinter as tk

import numpy as np

from .win_monitor import active_window_workarea


_BG = "#1e1e2e"
_FG_REC = "#f38ba8"
_FG_TRANS = "#f9e2af"
_FG_IDLE = "#a6e3a1"
_FG_ERR = "#eba0ac"

# Visualizer-Farbverlauf (unten -> oben, per Level)
_BAR_LOW = "#74c7ec"
_BAR_MID = "#b4befe"
_BAR_HI = "#f38ba8"

# Layout
_WIDTH = 420
_HEIGHT = 140
_CANVAS_H = 64
_PAD_X = 14
_BAR_GAP = 3
_BARS = 48

# Spektrum: log-Frequenzbereich fuer Sprache
_SR = 16000
_F_MIN = 120.0
_F_MAX = 6000.0
_FFT_BUF = 4096   # rollender Puffer fuer bessere Frequenzaufloesung

# Glaettung (exponential): 0 = instant, 1 = no update
_SMOOTH_UP = 0.5
_SMOOTH_DOWN = 0.12


def _lerp_color(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _color_for_level(lvl: float) -> str:
    if lvl < 0.5:
        return _lerp_color(_BAR_LOW, _BAR_MID, lvl * 2)
    return _lerp_color(_BAR_MID, _BAR_HI, (lvl - 0.5) * 2)


class Overlay:
    """Status + Audio-Visualizer. Alle UI-Aufrufe aus anderen Threads
    ueber `root.after(0, ...)` delegieren."""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-alpha", 0.94)
        self._root.configure(bg=_BG)
        self._root.geometry(f"{_WIDTH}x{_HEIGHT}+0+0")

        self._label = tk.Label(
            self._root,
            text="",
            fg=_FG_IDLE,
            bg=_BG,
            font=("Segoe UI", 13, "bold"),
            pady=6,
        )
        self._label.pack(fill="x", padx=_PAD_X, pady=(14, 0))

        self._hint = tk.Label(
            self._root,
            text="",
            fg="#6c7086",
            bg=_BG,
            font=("Segoe UI", 9),
        )
        self._hint.pack(fill="x", padx=_PAD_X)

        self._canvas = tk.Canvas(
            self._root,
            width=_WIDTH - 2 * _PAD_X,
            height=_CANVAS_H,
            bg=_BG,
            highlightthickness=0,
        )
        self._canvas.pack(padx=_PAD_X, pady=(6, 12))

        self._bar_items: list[int] = []
        self._init_bars()

        # Pegel pro Band (fix positioniert, nur Hoehe aendert sich)
        self._levels: np.ndarray = np.zeros(_BARS, dtype=np.float32)
        # Rollender Audio-Puffer fuer FFT
        self._audio_buf: np.ndarray = np.zeros(_FFT_BUF, dtype=np.float32)

        self._root.withdraw()

    # ----- Public API -----

    @property
    def root(self) -> tk.Tk:
        return self._root

    def show_recording(self) -> None:
        self._position_on_active_monitor()
        self._set_status("● Aufnahme läuft – sprich jetzt",
                         "Nochmal Hotkey = Stopp & Transkribieren", _FG_REC)
        self._levels = np.zeros(_BARS, dtype=np.float32)
        self._redraw_bars()
        self._root.deiconify()
        self._root.lift()
        self._root.attributes("-topmost", True)
        self._root.update_idletasks()

    def show_transcribing(self) -> None:
        self._set_status("⏳ Transkribiere …", "einen Moment bitte", _FG_TRANS)
        self._levels = np.zeros(_BARS, dtype=np.float32)
        self._redraw_bars()
        self._root.update_idletasks()

    def show_error(self, msg: str) -> None:
        self._position_on_active_monitor()
        self._set_status(f"⚠ {msg[:80]}", "", _FG_ERR)
        self._root.deiconify()
        self._root.lift()
        self._root.after(4500, self.hide)

    def show_info(self, text: str, hint: str = "", duration_ms: int = 3000) -> None:
        self._position_on_active_monitor()
        self._set_status(text, hint, _FG_IDLE)
        self._levels = np.zeros(_BARS, dtype=np.float32)
        self._redraw_bars()
        self._root.deiconify()
        self._root.lift()
        self._root.after(duration_ms, self.hide)

    def hide(self) -> None:
        self._root.withdraw()

    def update_audio(self, samples: np.ndarray) -> None:
        """Aus beliebigem Thread aufrufbar. Roh-Samples (float32, mono)."""
        try:
            self._root.after(0, self._push_audio, samples)
        except RuntimeError:
            pass

    # ----- Intern -----

    def _set_status(self, text: str, hint: str, color: str) -> None:
        self._label.configure(text=text, fg=color)
        self._hint.configure(text=hint)

    def _position_on_active_monitor(self) -> None:
        wa = active_window_workarea()
        x = wa.right - _WIDTH - 28
        y = wa.bottom - _HEIGHT - 28
        self._root.geometry(f"{_WIDTH}x{_HEIGHT}+{x}+{y}")

    def _init_bars(self) -> None:
        w = _WIDTH - 2 * _PAD_X
        bar_w = max(3, (w - (_BARS - 1) * _BAR_GAP) // _BARS)
        x = 0
        for _ in range(_BARS):
            # Start mit Nullhoehe am Boden; wachsen nach oben.
            item = self._canvas.create_rectangle(
                x, _CANVAS_H, x + bar_w, _CANVAS_H,
                fill=_BAR_LOW, outline="",
            )
            self._bar_items.append(item)
            x += bar_w + _BAR_GAP

    def _push_audio(self, samples: np.ndarray) -> None:
        if samples.size == 0:
            return
        # Rollenden Puffer updaten
        n = samples.size
        if n >= self._audio_buf.size:
            self._audio_buf[:] = samples[-self._audio_buf.size:]
        else:
            self._audio_buf[:-n] = self._audio_buf[n:]
            self._audio_buf[-n:] = samples

        new_levels = _compute_spectrum(self._audio_buf, _BARS)
        up = new_levels > self._levels
        self._levels = np.where(
            up,
            self._levels + _SMOOTH_UP * (new_levels - self._levels),
            self._levels + _SMOOTH_DOWN * (new_levels - self._levels),
        ).astype(np.float32)
        self._redraw_bars()

    def _redraw_bars(self) -> None:
        w = _WIDTH - 2 * _PAD_X
        bar_w = max(3, (w - (_BARS - 1) * _BAR_GAP) // _BARS)
        x = 0
        max_h = _CANVAS_H - 2
        for i, item in enumerate(self._bar_items):
            lvl = float(self._levels[i]) if i < len(self._levels) else 0.0
            h = int(lvl * max_h)
            self._canvas.coords(item, x, _CANVAS_H - h, x + bar_w, _CANVAS_H)
            self._canvas.itemconfigure(item, fill=_color_for_level(lvl))
            x += bar_w + _BAR_GAP


# --- Spektrum-Berechnung (FFT, log-Frequenz-Bins) ---

_LOG_EDGES: np.ndarray | None = None


def _log_edges(n_bars: int) -> np.ndarray:
    global _LOG_EDGES
    if _LOG_EDGES is None or _LOG_EDGES.size != n_bars + 1:
        _LOG_EDGES = np.logspace(np.log10(_F_MIN), np.log10(_F_MAX), n_bars + 1)
    return _LOG_EDGES


_EQ: np.ndarray | None = None


def _band_eq(n_bars: int) -> np.ndarray:
    """Per-Bar-Equalizer: Bass daempfen, Hoehen anheben,
    damit Sprache ueber alle Baender gut sichtbar ist."""
    global _EQ
    if _EQ is None or _EQ.size != n_bars:
        # Smooth ramp von 0.35 (Bass) bis 2.4 (Hoehen)
        _EQ = np.linspace(0.35, 2.4, n_bars).astype(np.float32)
    return _EQ


def _compute_spectrum(samples: np.ndarray, n_bars: int) -> np.ndarray:
    """Rechnet FFT → log-gebinntes Leistungsspektrum → 0..1 pro Bar."""
    n = samples.size
    if n < 64:
        return np.zeros(n_bars, dtype=np.float32)

    # DC entfernen (Mikro-Bias / Raumrauschen-Offset)
    sig = samples - float(samples.mean())
    # Fenster
    window = np.hanning(n).astype(np.float32)
    # /n normalisieren, damit Werte unabh. von Puffergroesse sind
    spec = np.abs(np.fft.rfft(sig * window)) / float(n)
    freqs = np.fft.rfftfreq(n, d=1.0 / _SR)

    edges = _log_edges(n_bars)
    bars = np.zeros(n_bars, dtype=np.float32)
    for i in range(n_bars):
        lo, hi = edges[i], edges[i + 1]
        mask = (freqs >= lo) & (freqs < hi)
        if mask.any():
            # Peak statt Mean – verhindert "Verschmieren"
            bars[i] = float(spec[mask].max())

    # Kompressive Skala (Wurzel) + Per-Bar-EQ + finale Anpassung
    bars = np.sqrt(bars + 1e-9)
    bars *= _band_eq(n_bars)
    bars = np.clip(bars * 3.0, 0.0, 1.0)
    return bars
