from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database file location
DATABASE_URL = "sqlite:///./helpdesk.db"

# Create the database connection
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for database models
Base = declarative_base()


# Get a database session when needed
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()