from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.chat import router as chat_router
from backend.app.api.metrics import router as metrics_router
from backend.app.api.ingest import router as ingest_router
from backend.app.db.database import engine
from backend.app.db import models


# Initialize the FastAPI application [cite: 183, 184]
app = FastAPI(title="Multi-Agent RAG API")

# Configure CORS so your React frontend can communicate with the backend [cite: 183]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Your Vite frontend URL
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