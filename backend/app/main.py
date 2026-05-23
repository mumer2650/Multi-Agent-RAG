from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api.metrics import router as metrics_router
from app.api.ingest import router as ingest_router

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

# Health check endpoint to verify the server is running [cite: 186]
@app.get("/")
async def root():
    return {"message": "Backend server is active"}