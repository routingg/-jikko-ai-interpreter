@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Could not install packages. Install Python 3.10+ first.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8000"
py server.py
pause
