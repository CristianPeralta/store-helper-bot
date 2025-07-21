from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User as UserModel
from app.db.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[UserModel, UserCreate, UserUpdate]):
    """User repository with custom methods for user operations."""
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[UserModel]:
        """Get a user by email."""
        result = await db.execute(
            select(self.model).where(self.model.email == email)
        )
        return result.scalars().first()
    
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> UserModel:
        """Create a new user with hashed password."""
        db_obj = self.model(
            email=obj_in.email,
            name=obj_in.name,
            # Add password hashing here when implementing authentication
            # hashed_password=get_password_hash(obj_in.password),
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: UserModel, 
        obj_in: UserUpdate
    ) -> UserModel:
        """Update a user."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        # Handle password update if provided
        # if update_data.get("password"):
        #     hashed_password = get_password_hash(update_data["password"])
        #     del update_data["password"]
        #     update_data["hashed_password"] = hashed_password
            
        return await super().update(db, db_obj=db_obj, obj_in=update_data)


# Create a singleton instance
user_repo = UserRepository(UserModel)
