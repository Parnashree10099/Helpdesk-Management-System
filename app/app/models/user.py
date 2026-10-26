from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # Unique ID for every user
    id = Column(Integer, primary_key=True, index=True)

    # User's full name
    full_name = Column(String(100), nullable=False)

    # Email must be unique
    email = Column(String(255), unique=True, index=True, nullable=False)

    # Stores the hashed password, never the original password
    hashed_password = Column(String(255), nullable=False)

    # Role: user, agent, or admin
    role = Column(String(20), default="user", nullable=False)

    # Whether the account is active
    is_active = Column(Boolean, default=True, nullable=False)

    # When the account was created
    created_at = Column(DateTime(timezone=True), server_default=func.now())