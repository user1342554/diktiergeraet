@echo off
setlocal
cd /d "%~dp0"

echo === Diktiergeraet Install ===
echo.

if not exist .venv (
    echo [1/4] Erstelle virtuelle Umgebung (.venv)...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo FEHLER: venv konnte nicht erstellt werden.
        exit /b 1
    )
) else (
    echo [1/4] venv existiert bereits.
)

echo [2/4] Aktualisiere pip...
call .venv\Scripts\python.exe -m pip install --upgrade pip

echo [3/4] Installiere Abhaengigkeiten (kann ein paar Minuten dauern)...
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo FEHLER: pip install fehlgeschlagen.
    exit /b 1
)

echo [4/4] Pruefe CUDA + faster-whisper...
call .venv\Scripts\python.exe scripts\cuda_check.py

echo.
echo === Fertig. Starten mit run.bat ===
endlocal
