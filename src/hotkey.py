"""Globale Hotkeys via pynput.GlobalHotKeys."""
from __future__ import annotations

from typing import Callable, Optional

from pynput import keyboard


class HotkeyListener:
    """Mehrere Hotkeys: main (z.B. fuer Diktat-Toggle) + optional settings."""

    def __init__(
        self,
        hotkey: str,
        callback: Callable[[], None],
        settings_hotkey: Optional[str] = None,
        settings_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self._hotkey = hotkey
        self._callback = callback
        self._settings_hotkey = settings_hotkey
        self._settings_callback = settings_callback
        self._listener: Optional[keyboard.GlobalHotKeys] = None

    def _build_map(self) -> dict[str, Callable[[], None]]:
        m: dict[str, Callable[[], None]] = {self._hotkey: self._fire_main}
        if self._settings_hotkey and self._settings_callback:
            m[self._settings_hotkey] = self._fire_settings
        return m

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.GlobalHotKeys(self._build_map())
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None

    def set_hotkey(self, hotkey: str) -> None:
        self._hotkey = hotkey
        self.stop()
        self.start()

    def set_settings_hotkey(self, hotkey: Optional[str]) -> None:
        self._settings_hotkey = hotkey
        self.stop()
        self.start()

    def _fire_main(self) -> None:
        try:
            self._callback()
        except Exception as e:  # noqa: BLE001
            print(f"[hotkey] main callback Fehler: {e}")

    def _fire_settings(self) -> None:
        if self._settings_callback is None:
            return
        try:
            self._settings_callback()
        except Exception as e:  # noqa: BLE001
            print(f"[hotkey] settings callback Fehler: {e}")
