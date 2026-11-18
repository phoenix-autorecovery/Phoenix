@echo off
echo ========================================================
echo               PHOENIX AUTONOMOUS RECOVERY
echo         Starting Backend and Frontend Services...
echo ========================================================

REM Check if Python venv exists
if not exist "backend\.venv\Scripts\python.exe" (
    echo [!] Backend virtual environment not found. Creating...
    python -m venv backend\.venv
    call backend\.venv\Scripts\activate.bat
    pip install -r backend\requirements.txt
)

REM Start Backend API server in new window
echo [*] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "PHOENIX Backend (FastAPI)" cmd /k "backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

REM Check frontend node_modules
if not exist "frontend\node_modules" (
    echo [!] Frontend dependencies not found. Installing npm packages...
    cd frontend && npm install && cd ..
)

REM Start Frontend server in new window
echo [*] Starting Vite Frontend on http://127.0.0.1:5173 ...
start "PHOENIX Frontend (React/Vite)" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo ========================================================
echo PHOENIX Services Launched!
echo.
echo   Frontend Dashboard:  http://127.0.0.1:5173
echo   Backend REST API:    http://127.0.0.1:8000
echo   API Documentation:   http://127.0.0.1:8000/docs
echo   Default Admin:       admin@phoenix.io / phoenix123
echo ========================================================
echo.
pause
