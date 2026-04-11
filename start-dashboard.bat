@echo off
setlocal enabledelayedexpansion

echo =============================================
echo OpenClaw Task Manager Dashboard
echo =============================================
echo.

:: Kill any existing process on port 5173
wsl -u dosubuntu bash -c "fuser -k 5173/tcp 2>/dev/null" 2>nul

:: Check if already running
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo Dashboard is already running.
    echo Open http://localhost:5173 in your browser.
    goto :end
)

echo Starting dashboard...
echo.
echo Dashboard: http://localhost:5173
echo Press CTRL+C to stop.
echo.

:: Start via WSL using the prophecy venv Python (has Flask)
:: The dashboard.py script has Flask auto-detection as fallback
wsl -u dosubuntu bash -c "cd ~/clawd/projects/openclaw-task-manager/dashboard && /home/dosubuntu/clawd/projects/prophecy-news-tracker/venv/bin/python dashboard.py" 2>&1

:end
pause
endlocal
