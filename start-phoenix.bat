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

REM Detect available port for backend (default 8000, fallback 8001)
set BACKEND_PORT=8000
backend\.venv\Scripts\python.exe -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 8000)); s.close()" >nul 2>&1
if errorlevel 1 (
    echo [!] Port 8000 is occupied or locked by another process.
    echo [*] Automatically routing backend to port 8001...
    set BACKEND_PORT=8001
)

REM Start Backend API server in new window
echo [*] Starting FastAPI Backend on http://127.0.0.1:%BACKEND_PORT% ...
start "PHOENIX Backend (FastAPI)" cmd /k "backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port %BACKEND_PORT%"

REM Check frontend node_modules
if not exist "frontend\node_modules" (
    echo [!] Frontend dependencies not found. Installing npm packages...
    cd frontend && npm install && cd ..
)

REM Start Frontend server in new window
echo [*] Starting Vite Frontend on http://127.0.0.1:5173 ...
start "PHOENIX Frontend (React/Vite)" cmd /k "cd frontend && set VITE_BACKEND_URL=http://127.0.0.1:%BACKEND_PORT% && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo ========================================================
echo PHOENIX Services Launched!
echo.
echo   Frontend Dashboard:  http://127.0.0.1:5173
echo   Backend REST API:    http://127.0.0.1:%BACKEND_PORT%
echo   API Documentation:   http://127.0.0.1:%BACKEND_PORT%/docs
echo   Default Admin:       admin@phoenix.io / phoenix123
echo ========================================================
echo.
pause
