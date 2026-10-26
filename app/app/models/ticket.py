from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    # Unique ticket number
    id = Column(Integer, primary_key=True, index=True)

    # Short title describing the problem
    title = Column(String(200), nullable=False)

    # Detailed explanation of the problem
    description = Column(Text, nullable=False)

    # Ticket category: Technical, Billing, Account, Subscription, Other
    category = Column(String(30), nullable=False, default="Other")

    # Priority: Low, Medium, High, Urgent
    priority = Column(String(20), nullable=False, default="Medium")

    # Status: Open, In Progress, Waiting for User, Resolved, Closed
    status = Column(String(30), nullable=False, default="Open")

    # ID of the user who created the ticket
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # ID of the support agent assigned to the ticket
    assigned_agent_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    # Ticket creation and update times
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)