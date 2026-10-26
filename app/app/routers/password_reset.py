from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.password_reset import PasswordReset
from app.schemas.password_reset import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.utils.security import hash_password


router = APIRouter(
    prefix="/api/auth",
    tags=["Password Reset"]
)
@router.post("/forgot-password")
def forgot_password(
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == request_data.email)
        .first()
    )

    if not user:
        return {
            "message": "If the account exists, a reset request has been created."
        }

    # Generate a secure six-digit reset code
    reset_code = f"{secrets.randbelow(1_000_000):06d}"

    # Store only the hash of the reset code
    reset_code_hash = hashlib.sha256(
        reset_code.encode()
    ).hexdigest()

    # Expire the code after 10 minutes
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    # Invalidate any previous unused codes for this email
    (
        db.query(PasswordReset)
        .filter(
            PasswordReset.email == user.email,
            PasswordReset.is_used == False
        )
        .update({"is_used": True})
    )

    reset_request = PasswordReset(
        email=user.email,
        reset_code_hash=reset_code_hash,
        expires_at=expires_at,
        is_used=False
    )

    db.add(reset_request)
    db.commit()

    # Development only: show the code in the server terminal
    print(f"DEV PASSWORD RESET CODE for {user.email}: {reset_code}")

    return {
        "message": "If the account exists, a reset request has been created."
    }
@router.post("/reset-password")
def reset_password(
    request_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    # Find the user
    user = (
        db.query(User)
        .filter(User.email == request_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code."
        )

    # Hash the submitted reset code
    submitted_code_hash = hashlib.sha256(
        request_data.reset_code.encode()
    ).hexdigest()

    # Find the matching reset request
    reset_request = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.email == user.email,
            PasswordReset.reset_code_hash == submitted_code_hash,
            PasswordReset.is_used == False
        )
        .order_by(PasswordReset.created_at.desc())
        .first()
    )

    if not reset_request:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code."
        )

    # Check whether the code has expired
    expires_at = reset_request.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) >= expires_at:
        reset_request.is_used = True
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code."
        )

    # Save the new password securely
    user.hashed_password = hash_password(
        request_data.new_password
    )

    # Mark the code as used
    reset_request.is_used = True

    db.commit()

    return {
        "message": "Password reset successful. You can now log in."
    }