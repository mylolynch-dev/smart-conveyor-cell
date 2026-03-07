@echo off
title Smart Conveyor Sorting Cell

echo ============================================
echo  Smart Conveyor Sorting Cell - Launcher
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

:: Install dependencies if needed
echo [1/3] Checking dependencies...
pip install -r requirements.txt --quiet
echo       Done.
echo.

:: Start PLC Simulator in a new window
echo [2/3] Starting PLC Simulator (Modbus TCP :5020)...
start "PLC Simulator" cmd /k "python plc\simulator\plc_sim.py"
timeout /t 2 /nobreak >nul

:: Start HMI Backend in a new window
echo [3/3] Starting HMI Backend (http://localhost:8000)...
start "HMI Backend" cmd /k "python hmi\backend\app.py"
timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo  Both services are starting up.
echo  Open your browser to: http://localhost:8000
echo ============================================
echo.
echo Press any key to open the HMI in your browser...
pause >nul
start http://localhost:8000
