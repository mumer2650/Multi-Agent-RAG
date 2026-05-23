import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Get the absolute path to the root 'backend' folder
# Since this file is in backend/app/db/database.py, we go up 3 levels
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 2. Point to the 'storage/sqlite' directory (matching Umer's chroma_db structure)
SQLITE_DIR = os.path.join(BASE_DIR, "storage", "sqlite")

# Ensure the directory exists so SQLite doesn't crash trying to save a file there
os.makedirs(SQLITE_DIR, exist_ok=True)

# 3. Define the database URL and file name
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(SQLITE_DIR, 'sage_appliances.db')}"

# 4. Create the SQLAlchemy engine
# connect_args={"check_same_thread": False} is strictly required for SQLite in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 5. Create session and base class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to use in your FastAPI routes later
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()