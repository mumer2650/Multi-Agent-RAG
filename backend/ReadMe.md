### Folder Structure that we are following (slight changes possible)

backend/
├── app/
│ ├── api/
│ │ ├── chat.py # WebSocket routes for real-time streaming
│ │ └── metrics.py # REST API routes to fetch evaluation scores
│ │
│ ├── core/
│ │ └── config.py # Environment variables (CORS settings, DB paths)
│ │
│ ├── db/
│ │ ├── database.py # Setup for the SQLite engine and database session
│ │ └── models.py # SQLAlchemy models (defines the actual SQL tables)
│ │
│ ├── schemas/
│ │ ├── chat.py # Pydantic schemas for validating chat inputs/outputs
│ │ └── metrics.py # Pydantic schemas for sending clean data to React
│ │
│ ├── services/
│ │ └── ai_bridge.py # The function that actually calls Member 2's LangGraph agent
│ │
│ └── main.py # FastAPI app initialization and router inclusion
│
└── requirements.txt # fastapi, uvicorn, websockets, sqlalchemy, pydantic

uvicorn app.main:app --reload --port 8000
uvicorn backend.app.main:app --reload --port 8000
