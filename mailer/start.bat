@echo off
REM Start Mailer. Keep this window open while you (or your team) use it.
cd /d "%~dp0"
if not exist .venv (
    echo Run setup.bat first.
    pause
    exit /b 1
)
.venv\Scripts\python run.py
pause
