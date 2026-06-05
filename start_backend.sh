#!/bin/bash

# =========================================================
# MULTI-AGENT RAG - INTEGRATED BACKEND STARTUP SCRIPT
# =========================================================

echo "🚀 Starting Multi-Agent RAG Backend..."
echo ""

# =========================================================
# SETUP ENVIRONMENT
# =========================================================
echo "📦 Checking Python environment..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found. Activating..."
    source venv/Scripts/activate  # For Windows Git Bash
else
    echo "⚠️  No virtual environment found. Create one with: python -m venv venv"
    exit 1
fi

# =========================================================
# VERIFY DEPENDENCIES
# =========================================================
echo ""
echo "📚 Verifying dependencies..."
python -m pip list | grep -q "fastapi\|langgraph\|uvicorn" && echo "✅ Core dependencies found" || echo "⚠️  Installing dependencies..."

# =========================================================
# START BACKEND SERVER
# =========================================================
echo ""
echo "🔥 Starting FastAPI server on http://localhost:8000"
echo "   WebSocket endpoint: ws://localhost:8000/ws/chat"
echo ""
echo "To connect from frontend, use:"
echo "   const ws = new WebSocket('ws://localhost:8000/ws/chat')"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
