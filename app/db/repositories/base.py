from typing import Any, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.result import ChunkedIteratorResult
from pydantic import BaseModel

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base repository with default database operations."""
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """Initialize repository with model and database session."""
        self.model = model
        self.db = db
    
    async def get(self, id: UUID) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()
    
    async def get_multi(
        self, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        result = await self.db.execute(
            select(self.model)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.id)
        )
        return result.scalars().all()
    
    async def create(self, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in.dict())
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        *, 
        id: UUID, 
        obj_in: UpdateSchemaType | dict[str, Any]
    ) -> Optional[ModelType]:
        """Update a record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        if not update_data:
            return None
            
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**update_data)
            .returning(self.model)
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalars().first()
    
    async def delete(self, *, id: UUID) -> bool:
        """Delete a record by ID."""
        stmt = (
            delete(self.model)
            .where(self.model.id == id)
            .returning(self.model.id)
        )
        
        result = await self.db.execute(stmt)
        await self.db.commit()
        return bool(result.scalars().first())
