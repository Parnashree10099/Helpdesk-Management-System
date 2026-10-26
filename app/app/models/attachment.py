from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    # Unique ID for each attachment
    id = Column(Integer, primary_key=True, index=True)

    # The ticket this attachment belongs to
    ticket_id = Column(
        Integer,
        ForeignKey("tickets.id"),
        nullable=False
    )

    # The user who uploaded the file
    uploaded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    # Original filename
    filename = Column(String(255), nullable=False)

    # Actual saved filename or storage key
    stored_filename = Column(String(255), unique=True, nullable=False)

    # File location relative to our project
    file_path = Column(String(500), nullable=False)

    # When the file was uploaded
    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )