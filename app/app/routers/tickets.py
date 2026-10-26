from app.utils.rate_limiter import limiter
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketResponse
from app.dependencies.auth import get_current_user
from app.models.message import TicketMessage
from app.schemas.message import MessageCreate, MessageResponse
from sqlalchemy import desc, func
import os
import uuid

from pathlib import Path
from fastapi import File, UploadFile
from app.models.attachment import TicketAttachment
from app.models.audit_log import AuditLog
from app.schemas.attachment import AttachmentResponse
from app.models.notification import Notification
def create_audit_log(db, user_id, action, details=None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=details
    )

    db.add(log)
    db.commit()
router = APIRouter(
    prefix="/api/tickets",
    tags=["Tickets"]
)


@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
def create_ticket(
    request: Request,
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    allowed_categories = [
        "Technical", "Billing", "Account", "Subscription", "Other"
    ]

    allowed_priorities = ["Low", "Medium", "High", "Urgent"]

    if ticket_data.category not in allowed_categories:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket category."
        )

    if ticket_data.priority not in allowed_priorities:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket priority."
        )

    new_ticket = Ticket(
        title=ticket_data.title,
        description=ticket_data.description,
        category=ticket_data.category,
        priority=ticket_data.priority,
        created_by=current_user.id
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)
    create_audit_log(
        db,
        current_user.id,
        "TICKET_CREATED",
        f"Ticket ID: {new_ticket.id}, Title: {new_ticket.title}"
    )

    if current_user.id != 3:
        notification = Notification(
            user_id=3,
            title="New ticket created",
            message=f"Ticket #{new_ticket.id}: {new_ticket.title}"
        )
        db.add(notification)
        db.commit()

    return new_ticket
@router.get("/", response_model=list[TicketResponse])
def get_all_tickets(
    status_filter: str = None,
    priority_filter: str = None,
    category_filter: str = None,
    search: str = None,
sort_by: str = "created_at",
sort_order: str = "desc",
page: int = 1,
page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate pagination values
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page must be at least 1."
        )

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Page size must be between 1 and 100."
        )

    # Start with a query for all tickets
    query = db.query(Ticket)

    # Apply role-based access restrictions
    if current_user.role == "admin":
        pass

    elif current_user.role == "user":
        query = query.filter(
            Ticket.created_by == current_user.id
        )

    elif current_user.role == "agent":
        query = query.filter(
            Ticket.assigned_agent_id == current_user.id
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view tickets."
        )

    # Filter by status
    if status_filter:
        allowed_statuses = [
    "Open",
    "In Progress",
    "Waiting for User",
    "Resolved",
    "Closed"
]

        if status_filter not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid ticket status."
            )

        query = query.filter(
            Ticket.status == status_filter
        )

    # Filter by priority
    if priority_filter:
        allowed_priorities = [
            "Low", "Medium", "High", "Urgent"
        ]

        if priority_filter not in allowed_priorities:
            raise HTTPException(
                status_code=400,
                detail="Invalid ticket priority."
            )

        query = query.filter(
            Ticket.priority == priority_filter
        )

    # Filter by category
    if category_filter:
        allowed_categories = [
            "Technical", "Billing", "Account",
            "Subscription", "Other"
        ]

        if category_filter not in allowed_categories:
            raise HTTPException(
                status_code=400,
                detail="Invalid ticket category."
            )

        query = query.filter(
            Ticket.category == category_filter
        )

    # Show newest tickets first
   # Search tickets by title
    if search:
        query = query.filter(
        Ticket.title.ilike(f"%{search.strip()}%")
    )
        # Validate sorting
    allowed_sort_fields = {
    "id": Ticket.id,
    "title": Ticket.title,
    "status": Ticket.status,
    "priority": Ticket.priority,
    "category": Ticket.category,
    "created_at": Ticket.created_at
}
    if sort_by not in allowed_sort_fields:
        raise HTTPException(
        status_code=400,
        detail="Invalid sort field."
    )
    if sort_order not in ["asc", "desc"]:
        raise HTTPException(
        status_code=400,
        detail="Sort order must be asc or desc."
    )
    # Apply sorting
    sort_column = allowed_sort_fields[sort_by]
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    tickets = query.offset(offset).limit(page_size).all()

    return tickets

@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket_by_id(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Admins can view every ticket
    if current_user.role == "admin":
        return ticket

    # Regular users can view their own tickets
    if current_user.role == "user" and ticket.created_by == current_user.id:
        return ticket

    # Agents can view tickets assigned to them
    if current_user.role == "agent" and ticket.assigned_agent_id == current_user.id:
        return ticket

    raise HTTPException(
        status_code=403,
        detail="You do not have permission to view this ticket."
    )

@router.put("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Admins can update all tickets
    if current_user.role == "admin":
        pass

    # Users can update only tickets they created
    elif current_user.role == "user":
        if ticket.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only update tickets you created."
            )

    # Agents can update only tickets assigned to them
    elif current_user.role == "agent":
        if ticket.assigned_agent_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only update tickets assigned to you."
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update tickets."
        )

    allowed_categories = [
        "Technical", "Billing", "Account", "Subscription", "Other"
    ]
    allowed_priorities = ["Low", "Medium", "High", "Urgent"]

    if ticket_data.category not in allowed_categories:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket category."
        )

    if ticket_data.priority not in allowed_priorities:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket priority."
        )

    ticket.title = ticket_data.title
    ticket.description = ticket_data.description
    ticket.category = ticket_data.category
    ticket.priority = ticket_data.priority

    db.commit()
    db.refresh(ticket)
    create_audit_log(
    db,
    current_user.id,
    "TICKET_UPDATED",
    f"Ticket ID: {ticket.id}, Title: {ticket.title}"
)
    return ticket
@router.delete("/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the ticket
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id
    ).first()

    # Check whether the ticket exists
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Admins can delete any ticket
    if current_user.role == "admin":
        pass

    # Users can delete only tickets they created
    elif current_user.role == "user":
        if ticket.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete tickets you created."
            )

    # Agents can delete only tickets assigned to them
    elif current_user.role == "agent":
        if ticket.assigned_agent_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete tickets assigned to you."
            )

    # Reject any other role
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete tickets."
        )

    # Delete the ticket
    # Record the deletion before removing the ticket
    create_audit_log(
    db,
    current_user.id,
    "TICKET_DELETED",
    f"Ticket ID: {ticket.id}, Title: {ticket.title}"
)
    # Delete the ticket
    db.delete(ticket)
    db.commit()

    return {
        "message": "Ticket deleted successfully.",
        "ticket_id": ticket_id
    }

@router.patch("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Find the ticket
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Only admins and assigned agents can change ticket status
    if current_user.role == "admin":
        pass

    elif current_user.role == "agent":
        if ticket.assigned_agent_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only update the status of tickets assigned to you."
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Only admins and assigned agents can update ticket status."
        )

    # Check whether the status is valid
    allowed_statuses = [
        "Open",
        "In Progress",
        "Waiting for User",
        "Resolved",
        "Closed"
    ]

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Choose Open, In Progress, Waiting for User, Resolved, or Closed."
        )

    # Store the old status
    old_status = ticket.status

    # Update status and resolution timestamp
    ticket.status = new_status

    if new_status == "Resolved":
        if old_status != "Resolved":
            ticket.resolved_at = func.now()
    else:
        ticket.resolved_at = None

    # Save changes to the database
    db.commit()
    db.refresh(ticket)

    # Record the status change
    create_audit_log(
        db,
        current_user.id,
        "TICKET_STATUS_UPDATED",
        f"Ticket ID: {ticket.id}, Old Status: {old_status}, New Status: {new_status}"
    )

    return {
        "message": "Ticket status updated successfully.",
        "ticket_id": ticket.id,
        "new_status": ticket.status,
        "resolved_at": ticket.resolved_at
    }
@router.patch("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only admins can assign tickets
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can assign tickets."
        )

    # Find the ticket
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Find the selected agent
    agent = db.query(User).filter(
        User.id == agent_id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=404,
            detail="Agent not found."
        )

    # Make sure the selected user is an active agent
    if agent.role != "agent" or not agent.is_active:
        raise HTTPException(
            status_code=400,
            detail="The selected user is not an active support agent."
        )

    # Assign the ticket
    # Store the previous agent ID
    old_agent_id = ticket.assigned_agent_id
    # Assign the ticket
    ticket.assigned_agent_id = agent.id
    db.commit()
    db.refresh(ticket)
    # Record the assignment in the audit log
    create_audit_log(
        db,
        current_user.id,
        "TICKET_ASSIGNED",
        f"Ticket ID: {ticket.id}, Previous Agent ID: {old_agent_id}, New Agent ID: {agent.id}"
    )

    notification = Notification(
        user_id=agent.id,
        title="Ticket assigned to you",
        message=f"Ticket #{ticket.id}: {ticket.title}"
    )
    db.add(notification)
    db.commit()

    return {
        "message": "Ticket assigned successfully.",
        "ticket_id": ticket.id,
        "assigned_agent_id": ticket.assigned_agent_id
    }

@router.post(
    "/{ticket_id}/messages/",
    response_model=MessageResponse
)
@limiter.limit("30/minute")
def send_ticket_message(
    request: Request,
    ticket_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Admins can access any ticket
    # Users can access their own tickets
    # Agents can access tickets assigned to them
    if current_user.role == "admin":
        pass
    elif current_user.role == "user" and ticket.created_by == current_user.id:
        pass
    elif current_user.role == "agent" and ticket.assigned_agent_id == current_user.id:
        pass
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to message this ticket."
        )

    new_message = TicketMessage(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        content=message_data.content
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    # Record the message in the audit log
        # Record the message in the audit log
    create_audit_log(
        db,
        current_user.id,
        "TICKET_MESSAGE_SENT",
        f"Ticket ID: {ticket_id}, Message ID: {new_message.id}"
    )

    # Notify the ticket creator when an agent replies
    if current_user.role == "agent" and ticket.created_by != current_user.id:
        notification = Notification(
            user_id=ticket.created_by,
            title="New reply on your ticket",
            message=f"Ticket #{ticket.id}: {ticket.title}"
        )
        db.add(notification)
        db.commit()

    return new_message

@router.get("/{ticket_id}/messages/", response_model=list[MessageResponse])
def get_ticket_messages(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Check whether the current user can access this ticket
    if current_user.role == "admin":
        pass
    elif current_user.role == "user" and ticket.created_by == current_user.id:
        pass
    elif current_user.role == "agent" and ticket.assigned_agent_id == current_user.id:
        pass
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view these messages."
        )

    messages = (
        db.query(TicketMessage)
        .filter(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc(), TicketMessage.id.asc())
        .all()
    )

    return messages
@router.post(
    "/{ticket_id}/attachments/",
    response_model=AttachmentResponse
)
def upload_ticket_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check whether the ticket exists
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Check ticket permissions
    if current_user.role == "admin":
        pass
    elif current_user.role == "user" and ticket.created_by == current_user.id:
        pass
    elif current_user.role == "agent" and ticket.assigned_agent_id == current_user.id:
        pass
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to upload attachments to this ticket."
        )

    # Allow only selected file types
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Upload PDF, PNG, JPG, JPEG, or TXT files."
        )

    # Create the upload directory
    upload_directory = Path("uploads")
    upload_directory.mkdir(parents=True, exist_ok=True)

    # Generate a unique filename
    stored_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = upload_directory / stored_filename

    # Save the file, with a 5 MB size limit
    max_file_size = 5 * 1024 * 1024
    total_size = 0

    try:
        with file_path.open("wb") as destination:
            while True:
                chunk = file.file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > max_file_size:
                    raise HTTPException(
                        status_code=413,
                        detail="File is too large. Maximum size is 5 MB."
                    )

                destination.write(chunk)

        attachment = TicketAttachment(
            ticket_id=ticket_id,
            uploaded_by=current_user.id,
            filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path)
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        # Record the attachment upload in the audit log
        create_audit_log(
            db,
            current_user.id,
            "TICKET_ATTACHMENT_UPLOADED",
            f"Ticket ID: {ticket_id}, Attachment ID: {attachment.id}, Filename: {original_filename}"
        )

        return attachment

    except Exception:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise

    finally:
        file.file.close()

@router.get(
    "/{ticket_id}/attachments/",
    response_model=list[AttachmentResponse]
)
def get_ticket_attachments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Check ticket access permissions
    if current_user.role == "admin":
        pass
    elif current_user.role == "user" and ticket.created_by == current_user.id:
        pass
    elif current_user.role == "agent" and ticket.assigned_agent_id == current_user.id:
        pass
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view these attachments."
        )

    attachments = (
        db.query(TicketAttachment)
        .filter(TicketAttachment.ticket_id == ticket_id)
        .order_by(TicketAttachment.uploaded_at.asc())
        .all()
    )

    return attachments
@router.get("/{ticket_id}/attachments/{attachment_id}/download")
def download_ticket_attachment(
    ticket_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check whether the ticket exists
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )

    # Check ticket permissions
    if current_user.role == "admin":
        pass
    elif current_user.role == "user" and ticket.created_by == current_user.id:
        pass
    elif current_user.role == "agent" and ticket.assigned_agent_id == current_user.id:
        pass
    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to download this attachment."
        )

    # Find the attachment belonging to this ticket
    attachment = (
        db.query(TicketAttachment)
        .filter(
            TicketAttachment.id == attachment_id,
            TicketAttachment.ticket_id == ticket_id
        )
        .first()
    )

    if not attachment:
        raise HTTPException(
            status_code=404,
            detail="Attachment not found."
        )

    # Confirm the stored file exists
    file_path = Path(attachment.file_path)

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="The attachment file could not be found."
        )

    return FileResponse(
        path=str(file_path),
        filename=attachment.filename,
        media_type="application/octet-stream"
    )