#!/usr/bin/env bash
set -e

echo "========================================================"
echo "              PHOENIX AUTONOMOUS RECOVERY               "
echo "        Starting Backend and Frontend Services...       "
echo "========================================================"

# Virtual environment check
if [ ! -d "backend/.venv" ]; then
    echo "[!] Creating Python virtual environment..."
    python3 -m venv backend/.venv
    source backend/.venv/bin/activate
    pip install --upgrade pip
    pip install -r backend/requirements.txt
fi

# Frontend dependencies check
if [ ! -d "frontend/node_modules" ]; then
    echo "[!] Installing Frontend npm dependencies..."
    cd frontend && npm install && cd ..
fi

echo "[*] Starting FastAPI Backend on http://127.0.0.1:8000 ..."
backend/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "[*] Starting Vite Frontend on http://127.0.0.1:5173 ..."
(cd frontend && npm run dev -- --host 127.0.0.1 --port 5173) &
FRONTEND_PID=$!

echo ""
echo "========================================================"
echo "PHOENIX Services Launched!"
echo ""
echo "  Frontend Dashboard:  http://127.0.0.1:5173"
echo "  Backend REST API:    http://127.0.0.1:8000"
echo "  API Documentation:   http://127.0.0.1:8000/docs"
echo "  Default Admin:       admin@phoenix.io / phoenix123"
echo "========================================================"
echo ""
echo "Press Ctrl+C to stop all services."

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT
wait
