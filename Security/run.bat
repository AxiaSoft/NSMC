@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM ==========================================================================
REM  NSMC bot launcher (Windows)
REM  Usage: double-click this file, or run:  run.bat
REM  It picks the right Python, installs dependencies if needed, then starts
REM  the bot WITH PYTHON (never with a shell).
REM  If your Python lives somewhere else, edit the PY variable below.
REM ==========================================================================

set "PY=C:\Python314\python.exe"
if not exist "%PY%" set "PY=python"

echo [i] Python interpreter: %PY%
"%PY%" -c "import sys; print('[i] Python', sys.version.split()[0])"
if errorlevel 1 (
    echo [X] Python was not found. Install it from https://www.python.org/downloads/
    echo     or edit the PY variable at the top of this file.
    pause
    exit /b 1
)

"%PY%" -c "import pyrogram" >nul 2>&1
if errorlevel 1 (
    echo [i] Telegram library is missing - installing from requirements.txt ...
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [X] Dependency installation failed.
        echo     Try manually:  "%PY%" -m pip install kurigram tgcrypto2
        pause
        exit /b 1
    )
)

"%PY%" -c "import pyrogram; print('[i] pyrogram module version:', pyrogram.__version__)"
echo [i] Starting the bot ...
echo ----------------------------------------------------------------------
"%PY%" bot.py
echo ----------------------------------------------------------------------
echo [i] Bot stopped.
pause
