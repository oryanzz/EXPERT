@echo off
rem Update EXPERT to the latest version. Your history, screenshots and settings are kept.
rem (EXPERT can also update itself: a banner appears in the app when a new version is out.)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\update.ps1" -Restart
if errorlevel 1 pause
