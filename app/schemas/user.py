from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field, field_validator

from . import BaseSchema

class UserBase(BaseSchema):
    """Base schema for User with common fields."""
    email: Optional[EmailStr] = Field(
        None,
        title="Email",
        description="User's email address (must be unique)",
        example="user@example.com"
    )
    name: Optional[str] = Field(
        None,
        title="Full Name",
        max_length=100,
        example="John Doe"
    )

class UserCreate(UserBase):
    """Schema for creating a new user."""
    email: EmailStr = Field(
        ...,
        title="Email",
        description="User's email address (must be unique)",
        example="user@example.com"
    )
    
    @field_validator('email')
    def email_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("Email cannot be empty")
        return v.lower().strip()

class UserUpdate(UserBase):
    """Schema for updating an existing user."""
    pass

class UserInDBBase(UserBase):
    """Base schema for user data stored in the database."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class User(UserInDBBase):
    """Schema for user data returned by the API."""
    pass

class UserInDB(UserInDBBase):
    """Schema for user data stored in the database (includes sensitive data)."""
    pass
