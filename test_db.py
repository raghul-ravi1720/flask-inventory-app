from sqlalchemy import text
from app.database import SessionLocal, engine
from app import models

def test_db_connection():
    db = SessionLocal()
    try:
        # Use SQLAlchemy's text() for raw SQL
        result = db.execute(text("SELECT 1"))
        print("Database connection successful:", result.scalar())
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    test_db_connection()
