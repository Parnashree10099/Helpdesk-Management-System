from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.utils.security import hash_password, verify_password
from app.utils.auth_token import create_access_token
from app.dependencies.auth import get_current_user
from app.dependencies.auth import require_role
from fastapi import Request
from app.utils.rate_limiter import limiter

# Create the authentication router
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# User registration endpoint
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    # Check whether the email is already registered
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists."
        )

    # Create a new user with a hashed password
    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role="user"
    )

    # Save the new user in the database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

# User login endpoint
@router.post("/login")
@limiter.limit("5/minute")
def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Find the user using their email
    user = (
        db.query(User)
        .filter(User.email == form_data.username)
        .first()
    )

    # Check whether the user exists and the password is correct
    if not user or not verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Check whether the account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive."
        )

    # Generate an authentication token
    access_token = create_access_token(
        user_id=user.id,
        role=user.role
    )

    # Return the token and basic user information
    return {
        "message": "Login successful!",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        }
    }

# Protected endpoint: get the currently logged-in user's profile
@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role
    }

# Admin-only test endpoint
@router.get("/admin-test")
def admin_test(
    current_user: User = Depends(require_role("admin"))
):
    return {
        "message": "Welcome, Admin!",
        "full_name": current_user.full_name,
        "role": current_user.role
    }