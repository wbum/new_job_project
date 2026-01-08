from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings


def _get_engine_kwargs(database_url: str) -> dict:
    """Return engine configuration based on database type."""
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    elif database_url.startswith("postgresql"):
        # Use NullPool for serverless/short-lived processes, or QueuePool with reasonable settings
        return {
            "pool_pre_ping": True,  # Verify connections before using
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }
    return {}


engine = create_engine(settings.DATABASE_URL, **_get_engine_kwargs(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
