from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    # Unique ID for each message
    id = Column(Integer, primary_key=True, index=True)

    # The ticket this message belongs to
    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id"),
        nullable=False
    )

    # The user or agent who sent the message
    sender_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    # The actual message
    content = Column(Text, nullable=False)

    # When the message was sent
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )