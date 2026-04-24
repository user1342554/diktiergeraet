@echo off
setlocal
cd /d "%~dp0"

set "SCRIPT_DIR=%~dp0"
set "TARGET=%SCRIPT_DIR%run.bat"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LINK=%STARTUP%\Diktiergeraet.lnk"

echo Erzeuge Autostart-Verknuepfung...
echo   Ziel:       %TARGET%
echo   Verknuepft: %LINK%

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LINK%');" ^
  "$s.TargetPath='%TARGET%';" ^
  "$s.WorkingDirectory='%SCRIPT_DIR%';" ^
  "$s.WindowStyle=7;" ^
  "$s.Description='Diktiergeraet – Lokales Whisper-Diktat';" ^
  "$s.Save()"

if errorlevel 1 (
    echo FEHLER beim Erstellen der Verknuepfung.
    exit /b 1
)

echo Fertig. Diktiergeraet startet ab dem naechsten Login automatisch.
echo Zum Entfernen: "%LINK%" loeschen.
endlocal
