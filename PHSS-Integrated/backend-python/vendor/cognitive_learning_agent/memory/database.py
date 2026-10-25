"""Database session management and schema initialization."""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from cognitive_learning_agent.config import settings
from cognitive_learning_agent.models.db_models import Base

# Engine configuration
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(custom_engine=None):
    """Create all tables in the database and perform safe lightweight migrations."""
    target_engine = custom_engine or engine
    Base.metadata.create_all(bind=target_engine)
    # Safe lightweight SQLite migration for new columns
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(target_engine)
        if inspector.has_table("learners"):
            existing_cols = [c["name"] for c in inspector.get_columns("learners")]
            if "recommended_path_json" not in existing_cols:
                with target_engine.connect() as conn:
                    conn.execute(text("ALTER TABLE learners ADD COLUMN recommended_path_json TEXT;"))
                    conn.commit()
    except Exception:
        pass


@contextmanager
def get_db_session() -> Session:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
