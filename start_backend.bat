@echo off
REM =========================================================
REM MULTI-AGENT RAG - INTEGRATED BACKEND STARTUP SCRIPT
REM =========================================================

echo 🚀 Starting Multi-Agent RAG Backend...
echo.

REM =========================================================
REM SETUP ENVIRONMENT
REM =========================================================
echo 📦 Checking Python environment...

REM Activate virtual environment if it exists
if exist "venv" (
    echo ✅ Virtual environment found. Activating...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  No virtual environment found. Create one with: python -m venv venv
    exit /b 1
)

REM =========================================================
REM START BACKEND SERVER
REM =========================================================
echo.
echo 🔥 Starting FastAPI server on http://localhost:8000
echo    WebSocket endpoint: ws://localhost:8000/ws/chat
echo.
echo To connect from frontend, use:
echo    const ws = new WebSocket('ws://localhost:8000/ws/chat')
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
