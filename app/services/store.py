import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import date

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.schemas.store import (
    StoreResponse,
    StoreHoursResponse,
    StoreContactResponse,
    StorePromotionsResponse,
)

class StoreService:
    """Service for managing static store information."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, data_file: Optional[Union[str, Path]] = None, _data: Optional[Dict] = None):
        """Implement singleton pattern with optional test override."""
        if cls._instance is None or _data is not None:
            cls._instance = super(StoreService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, data_file: Optional[Union[str, Path]] = None, _data: Optional[Dict] = None):
        """Initialize the store service with data file path or direct data."""
        if getattr(self, '_initialized', False) and _data is None:
            return
            
        if _data is not None:
            # For testing - use provided data directly
            self._store_data = _data
        else:
            if data_file is None:
                # Default to the data file in the app/data directory
                base_dir = Path(__file__).parent.parent
                self.data_file = base_dir / "data" / "store.json"
            else:
                self.data_file = Path(data_file)
            
            self._store_data = self._load_store_data()
        
        self._initialized = True
    
    def _load_store_data(self) -> Dict[str, Any]:
        """Load store data from the JSON file."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('store', {})
        except FileNotFoundError:
            raise RuntimeError(f"Store data file not found: {self.data_file}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in store data file: {e}")
    
    def get_store_info(self) -> StoreResponse:
        """Get complete store information."""
        try:
            return StoreResponse(**self._store_data)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid store data format: {str(e)}"
            )
    
    def get_store_hours(self) -> StoreHoursResponse:
        """Get store opening hours."""
        try:
            return StoreHoursResponse(hours=self._store_data['hours'])
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Missing hours data in store information: {str(e)}"
            )
    
    def get_contact_info(self) -> StoreContactResponse:
        """Get store contact information and social media links."""
        try:
            return StoreContactResponse(
                contact=self._store_data['contact'],
                social_media=self._store_data['social_media']
            )
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Missing contact or social media data: {str(e)}"
            )
    
    def get_promotions(self, active_only: bool = True) -> StorePromotionsResponse:
        """
        Get store promotions.
        
        Args:
            active_only: If True, return only promotions that haven't expired
            
        Returns:
            StorePromotionsResponse with the list of promotions
        """
        try:
            promotions = self._store_data.get('promotions', [])
            
            if active_only and promotions:
                today = date.today()
                promotions = [
                    p for p in promotions 
                    if date.fromisoformat(p['valid_until']) >= today
                ]
            
            return StorePromotionsResponse(promotions=promotions)
            
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing promotions: {str(e)}"
            )
    
    def get_payment_methods(self) -> List[str]:
        """Get accepted payment methods."""
        return self._store_data.get('payment_methods', [])
    
    def get_social_media_links(self) -> Dict[str, str]:
        """Get social media links."""
        return self._store_data.get('social_media', {})
    
    def get_location(self) -> Dict[str, str]:
        """Get store location information."""
        return self._store_data.get('location', {})


# Create a singleton instance
store_service = StoreService()
