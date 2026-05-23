from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Health check endpoint to verify the server is running [cite: 186]
@app.get("/")
async def root():
    return {"message": "Backend server is active"}