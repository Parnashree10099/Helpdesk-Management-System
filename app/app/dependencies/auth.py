from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.auth_token import verify_access_token


# Tell FastAPI where users can obtain their login token
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


# Get the currently logged-in user
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    # Check whether the token is valid
    try:
        payload = verify_access_token(token)

        # Get the user's ID from the token
        user_id = int(payload.get("sub"))

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Find the user in the database
    user = db.query(User).filter(User.id == user_id).first()

    # Make sure the user exists and is active
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is inactive.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user

# Check whether the logged-in user has the required role
def require_role(required_role: str):

    def role_checker(
        current_user=Depends(get_current_user)
    ):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource."
            )

        return current_user

    return role_checker