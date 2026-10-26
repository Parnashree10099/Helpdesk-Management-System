from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.utils.rate_limiter import limiter

from app.database import Base, engine

# Import all database models
from app.models.user import User
from app.models.ticket import Ticket
from app.models.message import TicketMessage
from app.models.attachment import TicketAttachment
from app.models.audit_log import AuditLog
from app.models.password_reset import PasswordReset

# Import the authentication router
from app.routers.auth import router as auth_router
from app.routers.tickets import router as tickets_router
from app.routers.admin import router as admin_router
from app.routers.password_reset import router as password_reset_router
from app.routers.notifications import router as notifications_router
from fastapi.middleware.cors import CORSMiddleware



# Create the FastAPI application
app = FastAPI(
    title="Helpdesk Management System",
    swagger_ui_parameters={"persistAuthorization": True}
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect rate limiting to FastAPI
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)


# Create all database tables
Base.metadata.create_all(bind=engine)


# Connect the authentication router
app.include_router(auth_router)

# Connect the ticket router
app.include_router(tickets_router)
app.include_router(admin_router)
app.include_router(password_reset_router)
app.include_router(notifications_router)


# Home page
@app.get("/")
def home():
    return {
        "message": "Helpdesk Management System API is working!"
    }