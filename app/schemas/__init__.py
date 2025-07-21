"""
Pydantic schemas for the application.

This module contains Pydantic models that define the data schemas used in the API.
These schemas are used for request/response validation and serialization.
"""
from datetime import datetime
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

# Generic type for paginated responses
DataT = TypeVar('DataT')

class BaseSchema(BaseModel):
    """Base schema with common fields and configuration."""
    class Config:
        orm_mode = True
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ResponseSchema(GenericModel, Generic[DataT]):
    """
    Generic response schema for API responses.
    
    Attributes:
        success: Whether the operation was successful
        message: Optional message describing the result
        data: The response data
    """
    success: bool = True
    message: Optional[str] = None
    data: Optional[DataT] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Re-export common types and base classes
__all__ = [
    'BaseSchema',
    'ResponseSchema',
    'DataT',
]
