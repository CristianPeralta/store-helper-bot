"""
Schemas package.

This package contains Pydantic models used for request/response validation
and serialization of data between the API and the database.
"""
from datetime import datetime
from typing import Generic, List, TypeVar

from pydantic import BaseModel

# Type variables for generic schema types
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseSchema(BaseModel):
    """Base schema with common fields and configuration."""
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        allow_population_by_field_name = True
        use_enum_values = True
        arbitrary_types_allowed = True


class ResponseSchema(BaseSchema):
    """Base response schema with common fields for API responses."""
    pass


class ListResponse(BaseModel, Generic[ModelType]):
    """
    Generic list response schema for paginated results.
    
    Attributes:
        items: List of items in the current page
        total: Total number of items
        page: Current page number
        page_size: Number of items per page
        pages: Total number of pages
    """
    items: List[ModelType]
    total: int
    page: int
    page_size: int
    pages: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
        allow_population_by_field_name = True
        use_enum_values = True
        arbitrary_types_allowed = True
