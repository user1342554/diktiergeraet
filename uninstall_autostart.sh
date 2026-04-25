#!/usr/bin/env bash
# Entfernt den Autostart-Eintrag.
set -euo pipefail

DESKTOP_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/diktiergeraet.desktop"

if [[ -f "$DESKTOP_FILE" ]]; then
    rm "$DESKTOP_FILE"
    echo "Autostart-Eintrag entfernt: $DESKTOP_FILE"
else
    echo "Kein Autostart-Eintrag gefunden ($DESKTOP_FILE)."
fi
