"""System-Tray-Icon mit Modell- und Sprachauswahl."""
from __future__ import annotations

from typing import Callable

import pystray
from PIL import Image, ImageDraw

from .config import AVAILABLE_LANGUAGES, AVAILABLE_MODELS, Config


def _make_icon() -> Image.Image:
    """Erzeugt ein einfaches Mikrofon-aehnliches Icon."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Mikrofon-Koerper (Rechteck abgerundet)
    d.rounded_rectangle((22, 10, 42, 40), radius=10, fill=(243, 139, 168, 255))
    # Staender
    d.rectangle((30, 40, 34, 52), fill=(243, 139, 168, 255))
    d.rectangle((20, 50, 44, 54), fill=(243, 139, 168, 255))
    # U-Buegel
    d.arc((18, 22, 46, 48), start=0, end=180, fill=(243, 139, 168, 255), width=3)
    return img


class Tray:
    def __init__(
        self,
        config: Config,
        on_model_change: Callable[[str], None],
        on_language_change: Callable[[str], None],
        on_open_settings: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._config = config
        self._on_model_change = on_model_change
        self._on_language_change = on_language_change
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit
        self._icon: pystray.Icon | None = None

    def _build_menu(self) -> pystray.Menu:
        def make_model_item(name: str) -> pystray.MenuItem:
            return pystray.MenuItem(
                name,
                lambda icon, item: self._set_model(name),
                checked=lambda item, n=name: self._config.model == n,
                radio=True,
            )

        def make_lang_item(code: str) -> pystray.MenuItem:
            label = {"de": "Deutsch", "en": "English", "auto": "Auto"}.get(code, code)
            return pystray.MenuItem(
                label,
                lambda icon, item: self._set_language(code),
                checked=lambda item, c=code: self._config.language == c,
                radio=True,
            )

        model_menu = pystray.Menu(*[make_model_item(m) for m in AVAILABLE_MODELS])
        lang_menu = pystray.Menu(*[make_lang_item(c) for c in AVAILABLE_LANGUAGES])

        return pystray.Menu(
            pystray.MenuItem(
                lambda item: f"Hotkey: {self._config.hotkey}",
                None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Modell", model_menu),
            pystray.MenuItem("Sprache", lang_menu),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Einstellungen…", lambda icon, item: self._on_open_settings()),
            pystray.MenuItem("Beenden", lambda icon, item: self._quit()),
        )

    def _set_model(self, name: str) -> None:
        self._config.model = name
        self._on_model_change(name)
        if self._icon:
            self._icon.update_menu()

    def _set_language(self, code: str) -> None:
        self._config.language = code
        self._on_language_change(code)
        if self._icon:
            self._icon.update_menu()

    def _quit(self) -> None:
        try:
            if self._icon:
                self._icon.stop()
        finally:
            self._on_quit()

    def start(self) -> None:
        self._icon = pystray.Icon(
            "Diktiergeraet",
            _make_icon(),
            "Diktiergeraet",
            self._build_menu(),
        )
        # run_detached startet das Icon in einem eigenen Thread.
        self._icon.run_detached()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()

    def refresh(self) -> None:
        """Nach extern geaenderter Config das Menue neu rendern."""
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass
