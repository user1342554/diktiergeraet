# Diktiergerät

Lokales Whisper-Diktat für Windows und Linux. Shortcut drücken, diktieren, Text wird ins aktive Feld eingefügt.

## Voraussetzungen
- **Windows 10/11** *oder* **Linux mit X11-Session** (Mint Cinnamon, MATE, XFCE — Wayland wird nicht unterstützt)
- Python 3.10+
- NVIDIA GPU empfohlen (mit aktuellem CUDA-Treiber)

## Installation

### Windows
```cmd
install.bat
```

### Linux (Mint/Ubuntu/Debian)
```bash
./install.sh
```
Prüft System-Pakete (`python3-venv`, `python3-tk`, `xclip`), legt ein `.venv` an und installiert die Python-Abhängigkeiten.

## Start

### Windows
```cmd
run.bat
```

### Linux
```bash
./run.sh
```

Das Tray-Icon (Mikrofon) erscheint im System-Tray bzw. Panel.

Standard-Shortcut: **Strg + Alt + Leertaste**

- 1× drücken → Aufnahme startet
- Nochmal drücken → Aufnahme stoppt, Transkription, Text wird ins aktive Textfeld geschrieben

Im Tray: Rechtsklick → Modell (tiny/base/small/medium/large-v3), Sprache (de/en/auto), Beenden.

## Autostart beim Login

### Windows
```cmd
install_autostart.bat
```
Entfernen:
```cmd
uninstall_autostart.bat
```

### Linux
```bash
./install_autostart.sh
```
Erzeugt einen XDG-Autostart-Eintrag in `~/.config/autostart/diktiergeraet.desktop`. Entfernen:
```bash
./uninstall_autostart.sh
```

## Konfiguration
- **Windows:** `%APPDATA%\Diktiergeraet\config.json`
- **Linux:** `~/.config/Diktiergeraet/config.json`

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

## Linux-Hinweise
- **Display-Server muss X11 sein**, nicht Wayland. Auf modernen Distros am Login-Screen die Session „Cinnamon" / „GNOME on Xorg" wählen, falls verfügbar.
- Tray-Icon: auf GNOME ohne AppIndicator-Extension wird es u.U. nicht sichtbar — Cinnamon/MATE/XFCE zeigen es nativ an.
- CUDA: faster-whisper findet die `nvidia-*-cu12` pip-Wheels automatisch. Falls du System-CUDA nutzt, kannst du die beiden `nvidia-*-cu12`-Zeilen in `requirements.txt` auskommentieren.
- Falls der Autostart-Eintrag nicht greift: prüfe in den Cinnamon-Einstellungen unter „Startanwendungen", ob „Diktiergeraet" aufgelistet und aktiviert ist.

## Fehlersuche
- **Windows:** `run_console.bat` (statt `run.bat`) zeigt Log-Ausgaben.
- **Linux:** `./run.sh` aus einem Terminal startet — Logs landen im Terminal-Fenster.
