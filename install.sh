#!/usr/bin/env bash
# Installiert Diktiergeraet-Abhaengigkeiten auf Linux (Mint/Ubuntu/Debian getestet).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

echo "=== Diktiergeraet Install (Linux) ==="
echo

# 1) System-Pakete pruefen (informativ — wir installieren nicht ungefragt)
NEEDED_PKGS=()
command -v python3 >/dev/null 2>&1 || NEEDED_PKGS+=("python3")
python3 -c "import venv" 2>/dev/null || NEEDED_PKGS+=("python3-venv")
python3 -c "import tkinter" 2>/dev/null || NEEDED_PKGS+=("python3-tk")
command -v xclip >/dev/null 2>&1 || command -v xsel >/dev/null 2>&1 || NEEDED_PKGS+=("xclip")

if (( ${#NEEDED_PKGS[@]} > 0 )); then
    echo "Folgende System-Pakete fehlen:"
    printf '  - %s\n' "${NEEDED_PKGS[@]}"
    echo
    echo "Installiere sie mit:"
    echo "  sudo apt install ${NEEDED_PKGS[*]}"
    echo
    read -r -p "Jetzt versuchen, mit 'sudo apt install' zu installieren? [y/N] " ans
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        sudo apt install -y "${NEEDED_PKGS[@]}"
    else
        echo "Abbruch — bitte System-Pakete manuell installieren und erneut starten."
        exit 1
    fi
fi

# 2) venv anlegen
if [[ ! -d .venv ]]; then
    echo "[1/3] Erstelle virtuelle Umgebung (.venv)…"
    python3 -m venv .venv
else
    echo "[1/3] venv existiert bereits."
fi

# 3) pip + Abhaengigkeiten
echo "[2/3] Aktualisiere pip…"
.venv/bin/python -m pip install --upgrade pip

echo "[3/3] Installiere Python-Abhaengigkeiten…"
.venv/bin/python -m pip install -r requirements.txt

echo
echo "=== Fertig. Starten mit ./run.sh ==="
echo "Hotkey-Default: Strg+Alt+Leertaste. Tray-Icon erscheint im Panel."
