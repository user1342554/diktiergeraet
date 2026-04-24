@echo off
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Diktiergeraet.lnk"
if exist "%LINK%" (
    del "%LINK%"
    echo Autostart-Verknuepfung entfernt.
) else (
    echo Keine Autostart-Verknuepfung vorhanden.
)
