import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.db.session import engine, Base
import app.models

def reset_database():
    print("⚠️ Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("✨ Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database reset complete.")

if __name__ == "__main__":
    reset_database()
