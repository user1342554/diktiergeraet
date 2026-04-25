"""Aperture-Overlay: floating pill mit runden Ecken, Status-Dot, Spektrum (CTk).

Cross-platform: auf Windows nutzt das Overlay den Chroma-Key-Trick fuer
runde, „schwebende" Ecken. Auf Linux (Tk hat kein `-transparentcolor`) wird
das Pill flach gerendert — gleicher Look-and-Feel, nur ohne den weichen
Aussenrand.
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import numpy as np

from .platform import active_window_workarea, configure_overlay_window


# --- Aperture tokens (dark) ------------------------------------------
_PANEL_BG = "#1c1c1e"      # dark solid pill surface
_INK = "#f5f5f7"           # label
_SUB = "#8e8e93"           # hint
_LINE = "#2c2c2e"          # hairline separator
_BORDER = "#3a3a3c"        # pill outline (fake hairline via 1px)

_FG_REC = "#ff453a"        # system red (dark tuned)
_FG_TRANS = "#ff9f0a"      # system orange (dark tuned)
_FG_IDLE = "#30d158"       # system green (dark tuned)

# Waveform: bright accent ramp that pops on dark panel
_BAR_LOW = "#355a93"
_BAR_MID = "#4a9dff"
_BAR_HI = "#7ec0ff"

# Chroma-key color for the rounded-corner transparency trick (Windows only).
# Must be picked carefully: Windows' -transparentcolor only keys pixels with
# an EXACT match, so anti-aliased edges of the rounded inner frame produce
# blend pixels that stay visible. Using hot magenta here created a visible
# purple halo. A chroma one step off the panel bg means the AA pixels blend
# between two near-identical darks — the halo vanishes into the panel.
_CHROMA = "#1d1d1f"

# Typography
_FONT = "Segoe UI Variable Text"
_FONT_DISP = "Segoe UI Variable Display"

# Layout (outer is pill — inner padding creates the "floating" feel)
_OUTER_PAD = 10            # chroma margin around pill (room for shadow-feel)
_PILL_W = 340
_PILL_H = 128
_WIDTH = _PILL_W + 2 * _OUTER_PAD
_HEIGHT = _PILL_H + 2 * _OUTER_PAD

_CANVAS_H = 56
_PAD_X = 14
_BAR_GAP = 3
_BARS = 32           # fewer bars → noticeably thicker and more present
_DOT_SIZE = 9

# Spectrum (log bins for speech)
_SR = 16000
_F_MIN = 120.0
_F_MAX = 6000.0
_FFT_BUF = 4096

_SMOOTH_UP = 0.5
_SMOOTH_DOWN = 0.12


# ─── Color helpers ─────────────────────────────────────
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
    """Aperture floating pill.  UI calls from other threads must go through
    ``root.after(0, …)`` — same contract as before."""

    def __init__(self) -> None:
        # Dark-Aperture palette
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._root = ctk.CTk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)

        # Plattformspezifisches Setup. Auf Windows stellt das den Chroma-Key
        # fuer runde, „schwebende" Ecken her. Auf Linux faerbt es das Root in
        # Panel-Farbe und schaltet den Splash-Type plus Window-Alpha.
        self._chroma_active = configure_overlay_window(self._root, _PANEL_BG, _CHROMA)

        if self._chroma_active:
            # Windows-Pfad: Chroma-Padding rund um das innere Pill
            self._win_w = _WIDTH
            self._win_h = _HEIGHT
            self._pill_x = _OUTER_PAD
            self._pill_y = _OUTER_PAD
        else:
            # Linux-/Fallback-Pfad: Window == Pill (kein sichtbarer Outer-Rand)
            self._win_w = _PILL_W
            self._win_h = _PILL_H
            self._pill_x = 0
            self._pill_y = 0

        self._root.geometry(f"{self._win_w}x{self._win_h}+0+0")

        # The pill — rounded CTkFrame inside the chroma-magenta window
        self._pill = ctk.CTkFrame(
            self._root,
            width=_PILL_W, height=_PILL_H,
            corner_radius=16,
            fg_color=_PANEL_BG,
            border_color=_BORDER,
            border_width=1,
        )
        self._pill.place(x=self._pill_x, y=self._pill_y)
        self._pill.pack_propagate(False)

        # ── Header row: status dot + label + elapsed ──
        header = ctk.CTkFrame(self._pill, fg_color="transparent", height=18)
        header.pack(fill="x", padx=_PAD_X, pady=(12, 0))

        # Status dot (small filled circle on its own canvas)
        self._dot_canvas = tk.Canvas(
            header, width=_DOT_SIZE + 2, height=_DOT_SIZE + 2,
            bg=_PANEL_BG, highlightthickness=0, bd=0,
        )
        self._dot_canvas.pack(side="left", padx=(0, 8))
        self._dot = self._dot_canvas.create_oval(
            1, 1, _DOT_SIZE + 1, _DOT_SIZE + 1,
            fill=_FG_IDLE, outline="",
        )

        self._label = ctk.CTkLabel(
            header, text="", text_color=_INK,
            font=(_FONT_DISP, 13, "bold"),
            anchor="w", justify="left",
        )
        self._label.pack(side="left", fill="x", expand=True)

        # ── Waveform canvas ──
        self._canvas = tk.Canvas(
            self._pill,
            width=_PILL_W - 2 * _PAD_X,
            height=_CANVAS_H,
            bg=_PANEL_BG,
            highlightthickness=0, bd=0,
        )
        self._canvas.pack(padx=_PAD_X, pady=(10, 0))

        # ── Hairline divider ──
        sep = ctk.CTkFrame(self._pill, fg_color=_LINE, height=1, corner_radius=0)
        sep.pack(fill="x", padx=_PAD_X, pady=(10, 0))

        # ── Footer hint ──
        self._hint = ctk.CTkLabel(
            self._pill, text="", text_color=_SUB,
            font=(_FONT, 10), anchor="w", justify="left",
        )
        self._hint.pack(fill="x", padx=_PAD_X, pady=(6, 10))

        # Bar storage
        self._bar_items: list[int] = []
        self._init_bars()

        # Level state per band + rolling audio buffer
        self._levels: np.ndarray = np.zeros(_BARS, dtype=np.float32)
        self._audio_buf: np.ndarray = np.zeros(_FFT_BUF, dtype=np.float32)

        self._root.withdraw()

    # ----- Public API -----------------------------------

    @property
    def root(self) -> tk.Tk:
        return self._root

    def show_recording(self) -> None:
        self._position_on_active_monitor()
        self._set_status(
            "Aufnahme läuft",
            "Hotkey nochmal = Stopp & Transkribieren",
            _FG_REC,
        )
        self._levels = np.zeros(_BARS, dtype=np.float32)
        self._redraw_bars()
        self._root.deiconify()
        self._root.lift()
        self._root.attributes("-topmost", True)
        self._root.update_idletasks()

    def show_transcribing(self) -> None:
        self._set_status("Transkribiere …", "einen Moment bitte", _FG_TRANS)
        self._levels = np.zeros(_BARS, dtype=np.float32)
        self._redraw_bars()
        self._root.update_idletasks()

    def show_error(self, msg: str) -> None:
        self._position_on_active_monitor()
        self._set_status(msg[:80], "", _FG_REC)
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

    # ----- Internals ------------------------------------

    def _set_status(self, text: str, hint: str, color: str) -> None:
        # Aperture: dot carries the state color; label stays ink-black.
        self._label.configure(text=text, text_color=_INK)
        self._hint.configure(text=hint)
        self._dot_canvas.itemconfigure(self._dot, fill=color)

    def _position_on_active_monitor(self) -> None:
        wa = active_window_workarea()
        # Margin von 14px zur Bildschirmkante, plattformunabhaengig.
        x = wa.right - self._win_w - 14
        y = wa.bottom - self._win_h - 14
        self._root.geometry(f"{self._win_w}x{self._win_h}+{x}+{y}")

    def _init_bars(self) -> None:
        # Thicker bars: at least 6px, with more stub height at rest
        w = _PILL_W - 2 * _PAD_X
        bar_w = max(6, (w - (_BARS - 1) * _BAR_GAP) // _BARS)
        x = 0
        for _ in range(_BARS):
            item = self._canvas.create_rectangle(
                x, _CANVAS_H - 3, x + bar_w, _CANVAS_H,
                fill=_BAR_LOW, outline="",
            )
            self._bar_items.append(item)
            x += bar_w + _BAR_GAP

    def _push_audio(self, samples: np.ndarray) -> None:
        if samples.size == 0:
            return
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
        w = _PILL_W - 2 * _PAD_X
        bar_w = max(6, (w - (_BARS - 1) * _BAR_GAP) // _BARS)
        x = 0
        max_h = _CANVAS_H - 2
        for i, item in enumerate(self._bar_items):
            lvl = float(self._levels[i]) if i < len(self._levels) else 0.0
            # Stronger minimum stub (3px) so the visualizer never looks dotted
            h = max(3, int(lvl * max_h))
            self._canvas.coords(item, x, _CANVAS_H - h, x + bar_w, _CANVAS_H)
            self._canvas.itemconfigure(item, fill=_color_for_level(lvl))
            x += bar_w + _BAR_GAP


# --- Spectrum: FFT → log bins → per-bar level ---

_LOG_EDGES: np.ndarray | None = None


def _log_edges(n_bars: int) -> np.ndarray:
    global _LOG_EDGES
    if _LOG_EDGES is None or _LOG_EDGES.size != n_bars + 1:
        _LOG_EDGES = np.logspace(np.log10(_F_MIN), np.log10(_F_MAX), n_bars + 1)
    return _LOG_EDGES


_EQ: np.ndarray | None = None


def _band_eq(n_bars: int) -> np.ndarray:
    global _EQ
    if _EQ is None or _EQ.size != n_bars:
        _EQ = np.linspace(0.35, 2.4, n_bars).astype(np.float32)
    return _EQ


def _compute_spectrum(samples: np.ndarray, n_bars: int) -> np.ndarray:
    n = samples.size
    if n < 64:
        return np.zeros(n_bars, dtype=np.float32)

    sig = samples - float(samples.mean())
    window = np.hanning(n).astype(np.float32)
    spec = np.abs(np.fft.rfft(sig * window)) / float(n)
    freqs = np.fft.rfftfreq(n, d=1.0 / _SR)

    edges = _log_edges(n_bars)
    bars = np.zeros(n_bars, dtype=np.float32)
    for i in range(n_bars):
        lo, hi = edges[i], edges[i + 1]
        mask = (freqs >= lo) & (freqs < hi)
        if mask.any():
            bars[i] = float(spec[mask].max())

    bars = np.sqrt(bars + 1e-9)
    bars *= _band_eq(n_bars)
    # Higher gain → visualizer reacts stronger to normal speech level
    bars = np.clip(bars * 4.5, 0.0, 1.0)
    return bars
