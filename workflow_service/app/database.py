from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Database URL (use DATABASE_URL env var if provided, otherwise file-based sqlite)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///workflow.db")

# sqlite needs check_same_thread=False for use with multiple threads (FastAPI/TestClient)
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Export a single SessionLocal for the application to import and reuse
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarative class for models
Base = declarative_base()

# Dependency for FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
