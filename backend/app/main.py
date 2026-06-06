from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from backend.app.api.chat import router as chat_router
from backend.app.api.metrics import router as metrics_router
from backend.app.api.ingest import router as ingest_router
from backend.app.db.database import engine
from backend.app.db import models
import os
from pathlib import Path

# Initialize the FastAPI application [cite: 183, 184]
app = FastAPI(title="Multi-Agent RAG API")

# Configure the directory for PDF serving
dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dataset")

@app.get("/static/{filename:path}")
async def serve_static_file(filename: str):
    # Strip any paths provided by the client, we just want the pure filename
    filename = os.path.basename(filename)
    base_dir = Path(dataset_dir)
    
    # Recursively search for the file inside the dataset directory
    for path in base_dir.rglob(filename):
        # Force the browser to render inline instead of downloading
        return FileResponse(
            str(path), 
            media_type="application/pdf", 
            headers={"Content-Disposition": "inline"}
        )
    return {"error": "File not found"}

# Configure CORS so your React frontend can communicate with the backend [cite: 183]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:9001",
        "http://127.0.0.1:9001",
        "http://localhost:9002",
        "http://127.0.0.1:9002"
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include the WebSocket chat router for the LangGraph integration
app.include_router(chat_router)
app.include_router(metrics_router)
app.include_router(ingest_router)

models.Base.metadata.create_all(bind=engine)

# Health check endpoint to verify the server is running [cite: 186]
@app.get("/")
async def root():
    return {"message": "Backend server is active"}