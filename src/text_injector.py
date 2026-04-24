"""Fuegt Text ins aktive Fenster ein via Clipboard + Strg+V."""
from __future__ import annotations

import time

import pyperclip
from pynput.keyboard import Controller, Key


_keyboard = Controller()


def inject_text(text: str, restore_delay_ms: int = 150) -> None:
    """Clipboard-Paste-Trick: alten Clipboard-Inhalt sichern, Text setzen,
    Strg+V senden, alten Inhalt wiederherstellen."""
    if not text:
        return

    # Altes Clipboard sichern (kann fehlschlagen, z.B. bei Binaerdaten)
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None

    try:
        pyperclip.copy(text)
    except Exception:
        # Clipboard nicht verfuegbar -> Fallback: direkt tippen
        _keyboard.type(text)
        return

    # Kurzer Moment, damit das Clipboard "sitzt"
    time.sleep(0.03)

    # Strg+V senden
    with _keyboard.pressed(Key.ctrl):
        _keyboard.press("v")
        _keyboard.release("v")

    # Clipboard spaeter zuruecksetzen (damit Paste durchgelaufen ist)
    time.sleep(restore_delay_ms / 1000.0)
    if previous is not None:
        try:
            pyperclip.copy(previous)
        except Exception:
            pass
