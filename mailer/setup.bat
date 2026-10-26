@echo off
REM One-time setup for Mailer on Windows. Double-click this file, or run it from a terminal.
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.11 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

if not exist .venv (
    echo Creating virtual environment...
    py -3 -m venv .venv || goto :error
)

echo Installing dependencies...
.venv\Scripts\python -m pip install --upgrade pip >nul
.venv\Scripts\python -m pip install -r requirements.txt || goto :error

if not exist .env (
    echo Creating .env with a random secret key...
    .venv\Scripts\python -c "import secrets, pathlib; t = pathlib.Path('.env.example').read_text(); pathlib.Path('.env').write_text(t.replace('SECRET_KEY=change-me', 'SECRET_KEY=' + secrets.token_hex(32)))" || goto :error
)

echo.
echo Setup complete. Double-click start.bat to run Mailer.
pause
exit /b 0

:error
echo.
echo Setup failed - see the messages above.
pause
exit /b 1
