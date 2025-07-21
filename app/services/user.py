from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User as UserModel
from app.repositories.user import user_repo
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.base import BaseService


class UserService(BaseService[UserModel, UserCreate, UserUpdate]):
    """User service with business logic for user operations."""
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[UserModel]:
        """Get a user by email."""
        return await user_repo.get_by_email(db, email=email)
    
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> UserModel:
        """Create a new user with validation."""
        # Check if user with email already exists
        db_user = await self.get_by_email(db, email=obj_in.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email already exists in the system.",
            )
        
        # Create the user
        return await user_repo.create(db, obj_in=obj_in)
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        id: int, 
        obj_in: UserUpdate
    ) -> Optional[UserModel]:
        """Update a user with validation."""
        db_obj = await user_repo.get(db, id=id)
        if not db_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Check if email is being updated and if it's already taken
        if obj_in.email and obj_in.email != db_obj.email:
            existing_user = await self.get_by_email(db, email=obj_in.email)
            if existing_user and existing_user.id != id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The email is already in use by another user.",
                )
        
        return await user_repo.update(db, db_obj=db_obj, obj_in=obj_in)
    
    async def authenticate(
        self, 
        db: AsyncSession, 
        *, 
        email: str, 
        password: str
    ) -> Optional[UserModel]:
        """Authenticate a user."""
        user = await self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def is_active(self, user: UserModel) -> bool:
        """Check if user is active."""
        return user.is_active
    
    def is_superuser(self, user: UserModel) -> bool:
        """Check if user is a superuser."""
        return user.is_superuser


# Create a singleton instance
user_service = UserService(user_repo)
