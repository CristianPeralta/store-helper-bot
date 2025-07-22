from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class ProductRating(BaseModel):
    """Schema for product rating."""
    rate: float = Field(..., ge=0, le=5, description="The average rating of the product")
    count: int = Field(..., ge=0, description="The number of ratings")


class ProductBase(BaseModel):
    """Base schema for product data."""
    title: str = Field(..., min_length=1, max_length=200, description="The title of the product")
    price: float = Field(..., gt=0, description="The price of the product")
    description: str = Field(..., min_length=1, description="The description of the product")
    category: str = Field(..., min_length=1, description="The category of the product")
    image: Optional[HttpUrl] = Field(None, description="URL of the product image")
    rating: Optional[ProductRating] = Field(None, description="Rating information")


class ProductCreate(ProductBase):
    """Schema for creating a new product (not used for FakeStore API, but included for completeness)."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product (not used for FakeStore API, but included for completeness)."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1)
    image: Optional[HttpUrl] = None


class ProductInDB(ProductBase):
    """Schema for product data stored in the database (not used for FakeStore API, but included for completeness)."""
    id: int = Field(..., description="The unique identifier for the product")


class Product(ProductInDB):
    """Schema for product data returned to the client."""
    pass


class ProductListResponse(BaseModel):
    """Schema for paginated list of products."""
    products: list[Product] = Field(default_factory=list, description="List of products")
    total: int = Field(0, description="Total number of products")
    skip: int = Field(0, description="Number of products skipped")
    limit: int = Field(0, description="Number of products per page")


class CategoryListResponse(BaseModel):
    """Schema for list of categories."""
    categories: list[str] = Field(default_factory=list, description="List of product categories")
