#!/usr/bin/env bash
# Erzeugt einen XDG-Autostart-Eintrag, sodass Diktiergeraet beim Login startet.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

PROJECT_DIR="$(pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/diktiergeraet.desktop"

mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Diktiergeraet
Comment=Lokales Whisper-Diktat
Exec=$PROJECT_DIR/run.sh
Path=$PROJECT_DIR
Icon=audio-input-microphone
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
Categories=Utility;AudioVideo;
EOF

chmod 644 "$DESKTOP_FILE"

echo "Autostart-Eintrag erstellt: $DESKTOP_FILE"
echo "Diktiergeraet startet ab dem naechsten Login automatisch."
echo "Zum Entfernen: ./uninstall_autostart.sh"
