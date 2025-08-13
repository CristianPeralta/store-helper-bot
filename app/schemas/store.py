from datetime import date
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


class Location(BaseModel):
    """Schema for store location information."""
    city: str = Field(..., description="City where the store is located")
    country: str = Field(..., description="Country where the store is located")
    address: str = Field(..., description="Full street address of the store")


class Contact(BaseModel):
    """Schema for store contact information."""
    phone: str = Field(..., description="Store contact phone number")
    email: str = Field(..., description="Store contact email")
    website: HttpUrl = Field(..., description="Store website URL")


class Hours(BaseModel):
    """Schema for store opening hours."""
    monday_to_friday: str = Field(..., description="Opening hours from Monday to Friday")
    saturday: str = Field(..., description="Opening hours on Saturday")
    sunday: str = Field(..., description="Opening hours on Sunday")


class Promotion(BaseModel):
    """Schema for store promotions."""
    title: str = Field(..., description="Title of the promotion")
    valid_until: date = Field(..., description="Last day the promotion is valid")


class SocialMedia(BaseModel):
    """Schema for store social media links."""
    facebook: Optional[HttpUrl] = Field(None, description="Facebook page URL")
    instagram: Optional[HttpUrl] = Field(None, description="Instagram profile URL")
    tiktok: Optional[HttpUrl] = Field(None, description="TikTok profile URL")


class StoreBase(BaseModel):
    """Base schema for store information."""
    name: str = Field(..., description="Name of the store")
    location: Location = Field(..., description="Store location details")
    contact: Contact = Field(..., description="Contact information")
    hours: Hours = Field(..., description="Store opening hours")
    promotions: List[Promotion] = Field(default_factory=list, description="Current promotions")
    payment_methods: List[str] = Field(default_factory=list, description="Accepted payment methods")
    social_media: SocialMedia = Field(..., description="Social media links")


class StoreResponse(StoreBase):
    """Response schema for store information."""
    pass


class StoreHoursResponse(BaseModel):
    """Response schema for store hours."""
    hours: Hours = Field(..., description="Store opening hours")


class StoreContactResponse(BaseModel):
    """Response schema for store contact information."""
    contact: Contact = Field(..., description="Contact information")
    social_media: SocialMedia = Field(..., description="Social media links")


class StorePromotionsResponse(BaseModel):
    """Response schema for store promotions."""
    promotions: List[Promotion] = Field(..., description="Current promotions")
