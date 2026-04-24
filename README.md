# Diktiergerät

Lokales Whisper-Diktat für Windows. Shortcut drücken, diktieren, Text wird ins aktive Feld eingefügt.

## Voraussetzungen
- Windows 10/11
- Python 3.10+
- NVIDIA GPU empfohlen (mit aktuellem CUDA-Treiber)

## Installation
```cmd
install.bat
```
Lädt CUDA-Runtime-Libs + faster-whisper und testet CUDA.

## Start
```cmd
run.bat
```
Das Tray-Icon (Mikrofon) erscheint unten rechts.

Standard-Shortcut: **Strg + Alt + Leertaste**

- 1× drücken → Aufnahme startet
- Nochmal drücken → Aufnahme stoppt, Transkription, Text wird ins aktive Textfeld geschrieben

Im Tray: Rechtsklick → Modell (tiny/base/small/medium/large-v3), Sprache (de/en/auto), Beenden.

## Autostart beim Login
```cmd
install_autostart.bat
```
Entfernen:
```cmd
uninstall_autostart.bat
```

## Konfiguration
`%APPDATA%\Diktiergeraet\config.json`
```json
{
  "model": "large-v3",
  "language": "de",
  "hotkey": "<ctrl>+<alt>+<space>",
  "device": "cuda",
  "compute_type": "float16",
  "paste_restore_delay_ms": 150
}
```

## Fehlersuche
Starte `run_console.bat` (statt `run.bat`), um Log-Ausgaben zu sehen.
