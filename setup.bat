@echo off
rem EXPERT setup: creates a private Python environment in .venv, installs the
rem dependencies and puts an EXPERT shortcut on the desktop. Safe to run again.
setlocal
cd /d "%~dp0"
title EXPERT setup
echo.
echo   EXPERT - EXP PER TIME : setup
echo   ------------------------------
echo.

rem onnxruntime needs Python 3.11+, the OCR package supports up to 3.12
set "PY="
for %%V in (3.12 3.11) do (
  if not defined PY ( py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V" )
)
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo Python 3.12 is required but was not found.
  echo.
  echo Install it with this command, then run setup.bat again:
  echo     winget install Python.Python.3.12
  echo or download it from https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)
echo Using: %PY%

if not exist ".venv\Scripts\python.exe" (
  echo Creating the Python environment...
  %PY% -m venv .venv || goto :fail
)
echo Installing dependencies (first time takes a minute)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet --upgrade pip || goto :fail
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements.txt || goto :fail

if not "%EXPERT_NO_SHORTCUT%"=="1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\make_shortcut.ps1" || goto :fail
)

echo.
echo   Done! Start EXPERT from the desktop shortcut (or run.bat).
echo.
pause
exit /b 0

:fail
echo.
echo   Setup failed - see the messages above.
echo.
pause
exit /b 1
