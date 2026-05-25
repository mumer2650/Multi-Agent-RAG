from backend.app.db.database import SessionLocal

def get_db_session():

    db = SessionLocal()

    try:
        return db

    except Exception:
        db.close()
        raise