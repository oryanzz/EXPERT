@echo off
rem Build dist\EXPERT.exe (single file) and self-test its OCR. Run setup.bat once first.
rem Releases are built by the "Release exe" GitHub workflow; this is for local builds.
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --quiet -r requirements-build.txt || goto :fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --log-level WARN EXPERT.spec || goto :fail
echo Self-testing dist\EXPERT.exe ...
start "" /wait "dist\EXPERT.exe" --selftest "tests\fixtures\sample_game.png" "dist\selftest.json"
if errorlevel 1 goto :fail
type "dist\selftest.json"
echo.
echo   Built dist\EXPERT.exe
exit /b 0
:fail
echo   Build failed.
exit /b 1
