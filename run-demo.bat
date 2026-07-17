@echo off
cd /d "%~dp0"
echo ==================================================
echo AI Demo launcher
echo ==================================================
echo.
echo This window should stay open and show progress.
echo.

if exist "backend\.venv\Scripts\python.exe" (
    echo Backend virtual environment found.
) else (
    echo Backend virtual environment not found. Creating it now...
    python -m venv backend\.venv   
)

echo.
echo Starting backend server...
start "AI Demo Backend" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe app.py"

echo.
echo Checking frontend tools...
where npm >nul 2>nul
if errorlevel 1 (
    echo npm not found. Opening backend page instead.
    timeout /t 3 >nul
    start "" http://127.0.0.1:5000/
) else (
    echo npm found. Starting frontend server...
    start "AI Demo Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"
    timeout /t 6 >nul
    start "" http://127.0.0.1:5173/
)

echo.
echo If the browser does not open, look at the new backend window for errors.
pause
