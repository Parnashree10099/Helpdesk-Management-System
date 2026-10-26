from pydantic import BaseModel, EmailStr, Field


# Information required when someone registers
class UserCreate(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )


# Information returned after registration
class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool

    model_config = {"from_attributes": True}

# Information required when a user logs in
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)