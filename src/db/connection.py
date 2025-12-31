# ============================================================
# Core DB connection
# ============================================================
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

import src.approval.models

SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite3"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Create tables
Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Dependency to provide DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

