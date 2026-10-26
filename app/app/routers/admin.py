from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.ticket import Ticket

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


# ADMIN DASHBOARD STATISTICS
@router.get("/dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Only admins can view dashboard statistics
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can view dashboard statistics."
        )

    # Count users by role
    total_users = db.query(User).filter(
        User.role == "user"
    ).count()

    total_agents = db.query(User).filter(
        User.role == "agent"
    ).count()

    # Count tickets by status
    open_tickets = db.query(Ticket).filter(
        Ticket.status == "Open"
    ).count()

    urgent_tickets = db.query(Ticket).filter(
        Ticket.priority == "Urgent"
    ).filter(
        Ticket.status.notin_(["Resolved", "Closed"])
    ).count()

    resolved_tickets = db.query(Ticket).filter(
        Ticket.status == "Resolved"
    ).count()
    # Calculate average resolution time in hours
    average_resolution_seconds = (
        db.query(
            func.avg(
                func.julianday(Ticket.resolved_at)
                - func.julianday(Ticket.created_at)
            ) * 86400
        )
        .filter(
            Ticket.status == "Resolved",
            Ticket.resolved_at.isnot(None)
        )
        .scalar()
    )

    average_resolution_hours = (
        round(average_resolution_seconds / 3600, 2)
        if average_resolution_seconds is not None
        else 0
    )

    # Count tickets created today
    today = func.current_date()

    tickets_created_today = db.query(Ticket).filter(
        func.date(Ticket.created_at) == today
    ).count()

    # Count tickets assigned to each agent
    agent_workload = (
        db.query(
            User.id,
            User.full_name,
            func.count(Ticket.id).label("assigned_tickets")
        )
        .outerjoin(
            Ticket,
            (Ticket.assigned_agent_id == User.id)
            & (Ticket.status.notin_(["Resolved", "Closed"]))
        )
        .filter(User.role == "agent")
        .group_by(User.id, User.full_name)
        .all()
    )

    # Get the five most recently created tickets
    recent_tickets = (
        db.query(Ticket)
        .order_by(Ticket.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_users": total_users,
        "total_agents": total_agents,
        "open_tickets": open_tickets,
        "urgent_tickets": urgent_tickets,
        "resolved_tickets": resolved_tickets,
        "average_resolution_hours": average_resolution_hours,
        "tickets_created_today": tickets_created_today,
        "agent_workload": [
            {
                "agent_id": agent.id,
                "agent_name": agent.full_name,
                "assigned_tickets": agent.assigned_tickets
            }
            for agent in agent_workload
        ],
        "recent_tickets": [
            {
                "id": ticket.id,
                "title": ticket.title,
                "priority": ticket.priority,
                "status": ticket.status,
                "created_by": ticket.created_by,
                "assigned_agent_id": ticket.assigned_agent_id,
                "created_at": ticket.created_at
            }
            for ticket in recent_tickets
        ]
    }


# VIEW AUDIT LOGS
@router.get("/audit-logs")
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Only admins can view audit logs
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can view audit logs."
        )

    # Prevent invalid pagination values
    if skip < 0 or limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination values."
        )

    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "created_at": log.created_at
        }
        for log in logs
    ]
# VIEW USER DETAILS AND ACTIVITY
@router.get("/users/{user_id}/activity")
def get_user_activity(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Only admins can view user activity
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can view user activity."
        )

    # Find the user
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    # Find tickets created by this user
    tickets = (
        db.query(Ticket)
        .filter(Ticket.created_by == user_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )

    # Find audit logs associated with this user
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.id.desc())
        .limit(20)
        .all()
    )

    return {
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at
        },
        "tickets": [
            {
                "id": ticket.id,
                "title": ticket.title,
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at,
                "resolved_at": ticket.resolved_at
            }
            for ticket in tickets
        ],
        "recent_activity": [
            {
                "id": log.id,
                "action": log.action,
                "details": log.details,
                "created_at": log.created_at
            }
            for log in logs
        ]
    }