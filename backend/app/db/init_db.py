from .database import engine, Base

# Import ALL models
# Without this import, SQLAlchemy will not detect your tables.

from backend.app.db.models import (Category,Product,ProductSpecification,ProductEmbedding,Review)

def initialize_database():

    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    print("Database initialized successfully.")

if __name__ == "__main__":
    initialize_database()