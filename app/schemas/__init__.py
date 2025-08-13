"""
Schemas package.

This package contains Pydantic models used for request/response validation
and serialization of data between the API and the database.
"""
from datetime import datetime
from typing import Generic, List, TypeVar, Any, Optional

from pydantic import BaseModel, ConfigDict, field_serializer

# Type variables for generic schema types
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseSchema(BaseModel):
    """Base schema with common fields and configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        validate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )
    
    @field_serializer('created_at', 'updated_at', check_fields=False)
    def serialize_dt(self, dt: Optional[datetime], _info: Any = None) -> Optional[str]:
        if dt is None:
            return None
        return dt.isoformat()


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

    model_config = ConfigDict(
        validate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 10,
                "pages": 0
            }
        }
    )
