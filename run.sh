#!/usr/bin/env bash
# Startet Diktiergeraet auf Linux (X11). Erwartet ein .venv im Projekt-Root.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

if [[ ! -d .venv ]]; then
    echo "FEHLER: .venv nicht gefunden. Bitte zuerst install.sh ausfuehren." >&2
    exit 1
fi

# Wayland-Warnung: pynput / pyperclip funktionieren auf Wayland nicht zuverlaessig.
if [[ "${XDG_SESSION_TYPE:-}" == "wayland" ]]; then
    echo "WARNUNG: Wayland-Session erkannt. Diktiergeraet braucht X11 — globale" >&2
    echo "Hotkeys und Text-Injection funktionieren auf Wayland nicht. In Mint:" >&2
    echo "  Ab-Login → Cinnamon (nicht 'Cinnamon (Software-Rendering)' o.ae.)" >&2
    echo "Trotzdem versuchen wir's…" >&2
fi

exec .venv/bin/python -m src.main "$@"
