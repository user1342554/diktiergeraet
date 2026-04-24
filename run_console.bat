@echo off
rem Start mit sichtbarem Konsolenfenster (zum Debuggen)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m src.main
