from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_class import Base
from app.db.repositories.base import BaseRepository

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base service with default CRUD operations."""
    
    def __init__(self, repository: BaseRepository[ModelType, CreateSchemaType, UpdateSchemaType]):
        """Initialize with a repository instance."""
        self.repository = repository
    
    async def get(self, db: AsyncSession, id: Union[UUID, int]) -> Optional[ModelType]:
        """Get a single record by ID."""
        return await self.repository.get(db, id=id)
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        **filters: Any
    ) -> List[ModelType]:
        """Get multiple records with optional filtering and pagination."""
        return await self.repository.get_multi(
            db, 
            skip=skip, 
            limit=limit, 
            **filters
        )
    
    async def create(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: CreateSchemaType,
        **extra_data: Any
    ) -> ModelType:
        """Create a new record."""
        return await self.repository.create(db, obj_in=obj_in, **extra_data)
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        id: Union[UUID, int],
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> Optional[ModelType]:
        """Update a record."""
        return await self.repository.update(db, id=id, obj_in=obj_in)
    
    async def delete(self, db: AsyncSession, *, id: Union[UUID, int]) -> bool:
        """Delete a record by ID."""
        return await self.repository.delete(db, id=id)
