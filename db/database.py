from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.base import Base

# SQLite database location
DATABASE_URL = "sqlite:///./saam.db"

# Engine configuration (SQLite requires check_same_thread=False)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
    future=True,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db():
    """
    FastAPI dependency that provides a database session.
    Yields a session and ensures it is closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Create all database tables defined in SQLAlchemy models.
    Safe to call multiple times.
    """
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully.")
    except Exception as e:
        print("Error initializing database:", e)
