@echo off
cd /d "%~dp0"
python -m learnctl serve --open
if errorlevel 1 (
  echo.
  echo Failed to start. Check Python 3.11+ and the current project path.
  pause
)
