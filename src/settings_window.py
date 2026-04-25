"""Aperture-Einstellungen: macOS-Window mit Sidebar (CTk-basiert)."""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk
import sounddevice as sd

from .config import AVAILABLE_LANGUAGES, AVAILABLE_MODELS, Config
from .model_downloader import download_model_async, is_downloaded


# --- Aperture tokens (dark) ------------------------------------------
_BG = "#1c1c1e"            # window background (bgSolid)
_BG_SIDEBAR = "#232325"    # sidebar (slightly deeper than main)
_BG_CARD = "#2a2a2c"       # field / card surface
_BG_HOVER = "#323234"      # sidebar / button hover
_INK = "#f5f5f7"           # primary ink
_SUB = "#8e8e93"           # secondary / hint / group caps
_LINE = "#2c2c2e"          # hairline separator

_ACCENT = "#0a84ff"        # system blue
_ACCENT_HOVER = "#3a9bff"
_ACCENT_PRESS = "#0070e0"

_OK = "#30d158"            # system green (dark tuned)
_WARN = "#ff9f0a"          # system orange (dark tuned)

_FONT = "Segoe UI Variable Text"
_FONT_DISP = "Segoe UI Variable Display"


def _input_devices() -> list[tuple[int, str]]:
    """(index, label) aller Input-Geräte."""
    out: list[tuple[int, str]] = []
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) >= 1:
            label = f"[{i}] {d['name']} ({int(d.get('default_samplerate', 0))} Hz)"
            out.append((i, label))
    return out


# ─── Sidebar item button ────────────────────────────────
class SidebarItem(ctk.CTkFrame):
    """Sidebar-Zeile: Icon + Label, Active-State mit Accent-Fill."""

    def __init__(self, master, *, icon: str, label: str, command) -> None:
        super().__init__(master, fg_color="transparent", corner_radius=6,
                         height=30, cursor="hand2")
        self.pack_propagate(False)
        self._command = command
        self._active = False
        self._icon = ctk.CTkLabel(self, text=icon, text_color=_SUB,
                                  font=(_FONT, 11), width=14)
        self._icon.pack(side="left", padx=(10, 8))
        self._label = ctk.CTkLabel(self, text=label, text_color=_INK,
                                   font=(_FONT, 12), anchor="w")
        self._label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        for w in (self, self._icon, self._label):
            w.bind("<Button-1>", lambda e: self._command())
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, _=None) -> None:
        if not self._active:
            self.configure(fg_color=_BG_HOVER)

    def _on_leave(self, _=None) -> None:
        if not self._active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self.configure(fg_color=_ACCENT)
            self._icon.configure(text_color="#ffffff")
            self._label.configure(text_color="#ffffff")
        else:
            self.configure(fg_color="transparent")
            self._icon.configure(text_color=_SUB)
            self._label.configure(text_color=_INK)


# ─── Settings window ────────────────────────────────────
class SettingsWindow:
    """Modales Einstellungsfenster im Aperture-Stil."""

    SECTIONS = [
        ("audio",    "◉", "Audio"),
        ("model",    "◈", "Modell"),
        ("language", "Aa", "Sprache"),
        ("shortcut", "⌘", "Kurzbefehl"),
    ]

    def __init__(
        self,
        parent: tk.Misc,
        config: Config,
        on_save: Callable[[Config], None],
    ) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._parent = parent
        self._cfg = config
        self._on_save = on_save

        self._win = ctk.CTkToplevel(parent)
        self._win.title("Diktiergerät — Einstellungen")
        self._win.geometry("760x540")
        self._win.resizable(False, False)
        self._win.configure(fg_color=_BG)
        try:
            self._win.transient(parent)  # type: ignore[arg-type]
        except Exception:
            pass

        self._current_section = "audio"
        self._sidebar_items: dict[str, SidebarItem] = {}

        self._build_ui()
        self._refresh_model_badge()
        self._select_section(self._current_section)

        self._win.update_idletasks()
        try:
            self._win.grab_set()
        except Exception:
            pass

    # ───────────────────────────── UI ─────────────────────────────

    def _build_ui(self) -> None:
        # Title bar (traffic lights + centered title)
        titlebar = ctk.CTkFrame(self._win, fg_color=_BG_SIDEBAR,
                                height=38, corner_radius=0)
        titlebar.pack(fill="x", side="top")
        titlebar.pack_propagate(False)

        lights = ctk.CTkFrame(titlebar, fg_color="transparent")
        lights.pack(side="left", padx=12)
        for color in ("#ff5f57", "#febc2e", "#28c840"):
            dot = ctk.CTkFrame(lights, width=12, height=12,
                               corner_radius=6, fg_color=color,
                               border_width=0)
            dot.pack(side="left", padx=3, pady=12)
        # First dot acts as close
        lights.winfo_children()[0].bind("<Button-1>", lambda e: self._close())

        title = ctk.CTkLabel(titlebar, text="Diktiergerät — Einstellungen",
                             text_color=_INK, font=(_FONT_DISP, 13, "bold"))
        title.place(relx=0.5, rely=0.5, anchor="center")

        # Hairline under titlebar
        tk.Frame(self._win, bg=_LINE, height=1).pack(fill="x")

        # Body: sidebar + main
        body = ctk.CTkFrame(self._win, fg_color=_BG, corner_radius=0)
        body.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(body, fg_color=_BG_SIDEBAR,
                               width=180, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Sidebar items
        for key, icon, label in self.SECTIONS:
            item = SidebarItem(sidebar, icon=icon, label=label,
                               command=lambda k=key: self._select_section(k))
            item.pack(fill="x", padx=8, pady=2)
            self._sidebar_items[key] = item
        # Top padding
        self._sidebar_items[self.SECTIONS[0][0]].pack_configure(pady=(12, 2))

        # Vertical hairline
        tk.Frame(body, bg=_LINE, width=1).pack(side="left", fill="y")

        # Main pane (scrollable)
        self._main = ctk.CTkFrame(body, fg_color=_BG, corner_radius=0)
        self._main.pack(side="left", fill="both", expand=True)

        self._pages: dict[str, ctk.CTkFrame] = {}
        self._build_audio_page()
        self._build_model_page()
        self._build_language_page()
        self._build_shortcut_page()

        # Footer with action buttons
        footer = ctk.CTkFrame(self._win, fg_color=_BG_SIDEBAR,
                              height=52, corner_radius=0)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        tk.Frame(footer, bg=_LINE, height=1).pack(fill="x", side="top")

        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.pack(side="right", padx=16, pady=10)

        cancel = ctk.CTkButton(
            btn_row, text="Abbrechen", command=self._close,
            width=90, height=30, corner_radius=8,
            fg_color=_BG_CARD, hover_color=_BG_HOVER,
            text_color=_INK, border_color=_LINE, border_width=1,
            font=(_FONT, 12),
        )
        cancel.pack(side="left", padx=(0, 8))

        save = ctk.CTkButton(
            btn_row, text="Speichern", command=self._save,
            width=100, height=30, corner_radius=8,
            fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
            text_color="#ffffff", border_width=0,
            font=(_FONT, 12, "bold"),
        )
        save.pack(side="left")

    # ───────── Pages ─────────

    def _new_page(self, section_title: str) -> ctk.CTkScrollableFrame:
        page = ctk.CTkScrollableFrame(self._main, fg_color=_BG, corner_radius=0)
        page.pack_forget()
        # Section header (small-caps style tracked label)
        ctk.CTkLabel(
            page, text=section_title.upper(),
            text_color=_SUB, font=(_FONT, 10, "bold"),
            anchor="w",
        ).pack(fill="x", anchor="w", pady=(4, 10), padx=(2, 2))
        return page

    def _row(self, page, label: str, *, hint: str = "") -> ctk.CTkFrame:
        row = ctk.CTkFrame(page, fg_color="transparent")
        row.pack(fill="x", pady=6)

        ctk.CTkLabel(row, text=label, text_color=_INK,
                     font=(_FONT, 12), anchor="w",
                     width=160).pack(side="left", padx=(0, 16), pady=(4, 0),
                                     anchor="n")
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="left", fill="x", expand=True)

        if hint:
            # Populated by caller on the returned "right" frame, hint below.
            pass
        row._right = right          # type: ignore[attr-defined]
        row._hint_text = hint       # type: ignore[attr-defined]
        return row

    def _row_commit_hint(self, row) -> None:
        hint = getattr(row, "_hint_text", "")
        if hint:
            ctk.CTkLabel(row._right, text=hint, text_color=_SUB,
                         font=(_FONT, 10), anchor="w",
                         justify="left", wraplength=420).pack(
                fill="x", anchor="w", pady=(4, 0),
            )

    # ── Audio page ──
    def _build_audio_page(self) -> None:
        page = self._new_page("Audio")

        devices = _input_devices()
        dev_labels = ["System-Default"] + [lbl for _, lbl in devices]
        self._devices = devices
        self._mic_var = tk.StringVar()
        cur_idx = self._cfg.input_device
        if cur_idx is None:
            self._mic_var.set("System-Default")
        else:
            match = next((lbl for i, lbl in devices if i == cur_idx), None)
            self._mic_var.set(match or "System-Default")

        row = self._row(page, "Eingabegerät")
        combo = ctk.CTkOptionMenu(
            row._right, values=dev_labels, variable=self._mic_var,
            width=400, height=28, corner_radius=6,
            fg_color=_BG_CARD, button_color=_BG_CARD,
            button_hover_color=_BG_HOVER, text_color=_INK,
            dropdown_fg_color=_BG_CARD, dropdown_text_color=_INK,
            dropdown_hover_color=_ACCENT,
            font=(_FONT, 12), dropdown_font=(_FONT, 12),
        )
        combo.pack(anchor="w")
        self._row_commit_hint(row)

        self._pages["audio"] = page

    # ── Model page ──
    def _build_model_page(self) -> None:
        page = self._new_page("Whisper-Modell")

        self._model_var = tk.StringVar(value=self._cfg.model)

        row = self._row(page, "Modell")
        model_menu = ctk.CTkOptionMenu(
            row._right, values=AVAILABLE_MODELS, variable=self._model_var,
            command=lambda *_: self._refresh_model_badge(),
            width=200, height=28, corner_radius=6,
            fg_color=_BG_CARD, button_color=_BG_CARD,
            button_hover_color=_BG_HOVER, text_color=_INK,
            dropdown_fg_color=_BG_CARD, dropdown_text_color=_INK,
            dropdown_hover_color=_ACCENT,
            font=(_FONT, 12), dropdown_font=(_FONT, 12),
        )
        model_menu.pack(side="left")

        self._model_badge = ctk.CTkLabel(
            row._right, text="", text_color=_SUB,
            font=(_FONT, 11),
        )
        self._model_badge.pack(side="left", padx=(12, 0))

        # Download row
        dl_row = self._row(page, "")
        self._download_btn = ctk.CTkButton(
            dl_row._right, text="Herunterladen",
            command=self._start_download,
            width=130, height=28, corner_radius=6,
            fg_color=_BG_CARD, hover_color=_BG_HOVER,
            text_color=_INK, border_color=_LINE, border_width=1,
            font=(_FONT, 12),
        )
        self._download_btn.pack(side="left")

        self._progress = ctk.CTkProgressBar(
            dl_row._right, width=260, height=6,
            corner_radius=3, fg_color=_LINE, progress_color=_ACCENT,
        )
        self._progress.set(0)
        self._progress.pack(side="left", padx=(12, 0), pady=(10, 0))

        self._progress_label = ctk.CTkLabel(
            page, text="", text_color=_SUB,
            font=(_FONT, 10), anchor="w",
        )
        self._progress_label.pack(fill="x", anchor="w", padx=(176, 0),
                                  pady=(2, 8))

        self._pages["model"] = page

    # ── Language page ──
    def _build_language_page(self) -> None:
        page = self._new_page("Allgemein")

        self._lang_var = tk.StringVar(value=self._cfg.language)
        row = self._row(page, "Sprache")

        # Segmented control from the available languages
        seg = ctk.CTkSegmentedButton(
            row._right, values=list(AVAILABLE_LANGUAGES),
            variable=self._lang_var,
            height=30, corner_radius=7,
            fg_color=_BG_SIDEBAR, selected_color=_ACCENT,
            selected_hover_color=_ACCENT_HOVER,
            unselected_color=_BG_SIDEBAR,
            unselected_hover_color=_BG_HOVER,
            text_color=_INK, text_color_disabled=_SUB,
            font=(_FONT, 12),
        )
        seg.pack(anchor="w")

        self._pages["language"] = page

    # ── Shortcut page ──
    def _build_shortcut_page(self) -> None:
        page = self._new_page("Kurzbefehl")

        self._hotkey_var = tk.StringVar(value=self._cfg.hotkey)
        row = self._row(page, "Diktieren",
                        hint="pynput-Format, z. B. <ctrl>+<alt>+<space>")
        entry = ctk.CTkEntry(
            row._right, textvariable=self._hotkey_var,
            width=260, height=28, corner_radius=6,
            fg_color=_BG_CARD, text_color=_INK,
            border_color=_LINE, border_width=1,
            font=(_FONT, 12),
        )
        entry.pack(anchor="w")
        self._row_commit_hint(row)

        # Info callout — matches Aperture's blue-tinted note
        # Accent-tinted callout for dark mode: 10% accent on black
        note = ctk.CTkFrame(page, fg_color="#0d2a4d",
                            border_color="#1f4b85", border_width=1,
                            corner_radius=8)
        note.pack(fill="x", pady=(18, 0), ipady=2)
        ctk.CTkLabel(
            note,
            text="Hinweis.  Tastenkombinationen werden global registriert — "
                 "sie funktionieren auch, wenn Diktiergerät nicht im Vordergrund ist.",
            text_color=_INK, font=(_FONT, 11),
            wraplength=460, justify="left", anchor="w",
        ).pack(fill="x", padx=12, pady=10)

        self._pages["shortcut"] = page

    # ───────── Section switching ─────────
    def _select_section(self, key: str) -> None:
        for k, item in self._sidebar_items.items():
            item.set_active(k == key)
        for k, page in self._pages.items():
            if k == key:
                page.pack(fill="both", expand=True, padx=28, pady=(20, 20))
            else:
                page.pack_forget()
        self._current_section = key

    # ───────── Model badge / download ─────────
    def _refresh_model_badge(self) -> None:
        m = self._model_var.get()
        if is_downloaded(m):
            self._model_badge.configure(text="✓ lokal verfügbar",
                                        text_color=_OK)
            self._download_btn.configure(text="Erneut prüfen")
        else:
            self._model_badge.configure(text="↓ nicht heruntergeladen",
                                        text_color=_WARN)
            self._download_btn.configure(text="Herunterladen")

    def _start_download(self) -> None:
        m = self._model_var.get()
        self._download_btn.configure(state="disabled")
        self._progress.set(0)
        self._progress_label.configure(text=f"Lade {m} …")

        def on_progress(done: int, total: int, desc: str) -> None:
            self._win.after(0, self._set_progress, done, total, desc)

        def on_done(err: Optional[Exception]) -> None:
            def finish() -> None:
                if err is None:
                    self._progress_label.configure(
                        text=f"{m}: Download abgeschlossen")
                    self._progress.set(1.0)
                else:
                    self._progress_label.configure(text=f"Fehler: {err}")
                self._download_btn.configure(state="normal")
                self._refresh_model_badge()
            self._win.after(0, finish)

        download_model_async(m, progress_cb=on_progress, on_done=on_done)

    def _set_progress(self, done: int, total: int, desc: str) -> None:
        if total <= 0:
            self._progress.set(0)
            return
        frac = min(1.0, done / total)
        self._progress.set(frac)
        mb_done = done / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self._progress_label.configure(
            text=f"{desc}  {mb_done:.0f} / {mb_total:.0f} MB  ({frac*100:.0f}%)"
        )

    # ───────── Save / close ─────────
    def _save(self) -> None:
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
