"""Einstellungs-Fenster (Tk Toplevel)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

import sounddevice as sd

from .config import AVAILABLE_LANGUAGES, AVAILABLE_MODELS, Config
from .model_downloader import download_model_async, is_downloaded


_BG = "#1e1e2e"
_FG = "#cdd6f4"
_ACCENT = "#89b4fa"
_MUTED = "#6c7086"


def _input_devices() -> list[tuple[int, str]]:
    """Liste aller Audio-Input-Geraete: (index, label)."""
    devices = sd.query_devices()
    out: list[tuple[int, str]] = []
    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) >= 1:
            label = f"[{i}] {d['name']} ({int(d.get('default_samplerate', 0))} Hz)"
            out.append((i, label))
    return out


class SettingsWindow:
    """Modales Einstellungsfenster. Muss auf dem Tk-Main-Thread laufen."""

    def __init__(
        self,
        parent: tk.Misc,
        config: Config,
        on_save: Callable[[Config], None],
    ) -> None:
        self._parent = parent
        self._cfg = config
        self._on_save = on_save

        self._win = tk.Toplevel(parent)
        self._win.title("Diktiergerät – Einstellungen")
        self._win.configure(bg=_BG)
        self._win.geometry("540x420")
        self._win.transient(parent)  # type: ignore[arg-type]

        self._build_style()
        self._build_ui()
        self._refresh_model_badge()

        # Zentriert auf dem Parent
        self._win.update_idletasks()
        self._win.grab_set()

    # ---------- UI Aufbau ----------

    def _build_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background=_BG)
        style.configure("TLabel", background=_BG, foreground=_FG, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground=_FG)
        style.configure("Muted.TLabel", foreground=_MUTED)
        style.configure(
            "TButton",
            background="#313244", foreground=_FG,
            padding=(10, 6), font=("Segoe UI", 10),
        )
        style.map("TButton",
            background=[("active", "#45475a")],
        )
        style.configure(
            "Accent.TButton",
            background=_ACCENT, foreground="#1e1e2e",
            padding=(10, 6), font=("Segoe UI", 10, "bold"),
        )
        style.map("Accent.TButton",
            background=[("active", "#b4befe")],
        )
        style.configure("TCombobox",
            fieldbackground="#313244", background="#313244",
            foreground=_FG, arrowcolor=_FG,
        )
        style.configure("Horizontal.TProgressbar",
            background=_ACCENT, troughcolor="#313244", borderwidth=0,
        )

    def _build_ui(self) -> None:
        frm = ttk.Frame(self._win, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Einstellungen", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10),
        )

        # --- Mikrofon ---
        ttk.Label(frm, text="Mikrofon:").grid(row=1, column=0, sticky="w", pady=6)
        self._devices = _input_devices()
        dev_labels = ["System-Default"] + [lbl for _, lbl in self._devices]
        self._mic_var = tk.StringVar()
        cur_idx = self._cfg.input_device
        if cur_idx is None:
            self._mic_var.set("System-Default")
        else:
            match = next((lbl for i, lbl in self._devices if i == cur_idx), None)
            self._mic_var.set(match or "System-Default")
        mic_combo = ttk.Combobox(
            frm, textvariable=self._mic_var, values=dev_labels,
            state="readonly", width=56,
        )
        mic_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=6)

        # --- Modell ---
        ttk.Label(frm, text="Modell:").grid(row=2, column=0, sticky="w", pady=6)
        self._model_var = tk.StringVar(value=self._cfg.model)
        model_combo = ttk.Combobox(
            frm, textvariable=self._model_var, values=AVAILABLE_MODELS,
            state="readonly", width=20,
        )
        model_combo.grid(row=2, column=1, sticky="w", pady=6)
        model_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_model_badge())

        self._model_badge = ttk.Label(frm, text="", style="Muted.TLabel")
        self._model_badge.grid(row=2, column=2, sticky="w", padx=(8, 0))

        self._download_btn = ttk.Button(
            frm, text="Herunterladen", command=self._start_download,
        )
        self._download_btn.grid(row=3, column=1, sticky="w", pady=(0, 6))

        self._progress = ttk.Progressbar(
            frm, mode="determinate", maximum=100, length=300,
        )
        self._progress.grid(row=3, column=2, sticky="ew", pady=(0, 6), padx=(8, 0))
        self._progress_label = ttk.Label(frm, text="", style="Muted.TLabel")
        self._progress_label.grid(row=4, column=1, columnspan=2, sticky="w", pady=(0, 10))

        # --- Sprache ---
        ttk.Label(frm, text="Sprache:").grid(row=5, column=0, sticky="w", pady=6)
        self._lang_var = tk.StringVar(value=self._cfg.language)
        ttk.Combobox(
            frm, textvariable=self._lang_var, values=AVAILABLE_LANGUAGES,
            state="readonly", width=20,
        ).grid(row=5, column=1, sticky="w", pady=6)

        # --- Hotkey ---
        ttk.Label(frm, text="Hotkey:").grid(row=6, column=0, sticky="w", pady=6)
        self._hotkey_var = tk.StringVar(value=self._cfg.hotkey)
        ttk.Entry(frm, textvariable=self._hotkey_var, width=30).grid(
            row=6, column=1, sticky="w", pady=6,
        )
        ttk.Label(
            frm,
            text="(pynput-Format: <ctrl>+<alt>+<space>)",
            style="Muted.TLabel",
        ).grid(row=6, column=2, sticky="w", padx=(8, 0))

        # --- Spacer ---
        frm.grid_columnconfigure(2, weight=1)

        # --- Buttons ---
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=10, column=0, columnspan=3, sticky="e", pady=(20, 0))
        ttk.Button(btn_frame, text="Abbrechen", command=self._close).pack(
            side="right", padx=(6, 0),
        )
        ttk.Button(
            btn_frame, text="Speichern", style="Accent.TButton", command=self._save,
        ).pack(side="right")

    # ---------- Actions ----------

    def _refresh_model_badge(self) -> None:
        m = self._model_var.get()
        if is_downloaded(m):
            self._model_badge.configure(text="✓ lokal verfügbar", foreground=_ACCENT)
            self._download_btn.configure(text="Erneut prüfen")
        else:
            self._model_badge.configure(text="⬇ nicht heruntergeladen", foreground="#f9e2af")
            self._download_btn.configure(text="Herunterladen")

    def _start_download(self) -> None:
        m = self._model_var.get()
        self._download_btn.configure(state="disabled")
        self._progress["value"] = 0
        self._progress_label.configure(text=f"Lade {m} …")

        def on_progress(done: int, total: int, desc: str) -> None:
            self._win.after(0, self._set_progress, done, total, desc)

        def on_done(err: Optional[Exception]) -> None:
            def finish() -> None:
                if err is None:
                    self._progress_label.configure(text=f"{m}: Download abgeschlossen")
                    self._progress["value"] = 100
                else:
                    self._progress_label.configure(text=f"Fehler: {err}")
                self._download_btn.configure(state="normal")
                self._refresh_model_badge()
            self._win.after(0, finish)

        download_model_async(m, progress_cb=on_progress, on_done=on_done)

    def _set_progress(self, done: int, total: int, desc: str) -> None:
        if total <= 0:
            self._progress["value"] = 0
            return
        pct = min(100.0, (done / total) * 100.0)
        self._progress["value"] = pct
        mb_done = done / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self._progress_label.configure(
            text=f"{desc}  {mb_done:.0f} / {mb_total:.0f} MB  ({pct:.0f}%)"
        )

    def _save(self) -> None:
        # Mikrofon
        mic_label = self._mic_var.get()
        if mic_label == "System-Default":
            self._cfg.input_device = None
        else:
            for i, lbl in self._devices:
                if lbl == mic_label:
                    self._cfg.input_device = i
                    break

        self._cfg.model = self._model_var.get()
        self._cfg.language = self._lang_var.get()
        new_hk = self._hotkey_var.get().strip()
        if new_hk:
            self._cfg.hotkey = new_hk

        try:
            self._on_save(self._cfg)
        finally:
            self._close()

    def _close(self) -> None:
        try:
            self._win.grab_release()
        except Exception:
            pass
        self._win.destroy()
