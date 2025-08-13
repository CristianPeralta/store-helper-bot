"""Integration tests for the StoreService."""
import json
from pathlib import Path
from datetime import date, timedelta
import pytest
from unittest.mock import mock_open, patch

from fastapi import HTTPException, status

from app.services.store import StoreService
from app.schemas.store import (
    StoreResponse,
    StoreHoursResponse,
    StoreContactResponse,
    StorePromotionsResponse
)

# Sample test data
SAMPLE_STORE_DATA = {
    "store": {
        "name": "Test Store",
        "location": {
            "city": "Test City",
            "country": "Test Country",
            "address": "123 Test St, Test City, 12345"
        },
        "contact": {
            "email": "test@example.com",
            "phone": "+1 (555) 123-4567",
            "website": "https://teststore.example.com"
        },
        "hours": {
            "monday_to_friday": "9:00 AM - 6:00 PM",
            "saturday": "10:00 AM - 5:00 PM",
            "sunday": "Closed"
        },
        "promotions": [
            {
                "title": "Summer Sale",
                "valid_until": (date.today() + timedelta(days=30)).isoformat()
            },
            {
                "title": "Expired Promo",
                "valid_until": (date.today() - timedelta(days=1)).isoformat()
            }
        ],
        "payment_methods": ["credit_card", "debit_card", "paypal"],
        "social_media": {
            "facebook": "https://facebook.com/teststore",
            "instagram": "https://instagram.com/teststore",
            "tiktok": None
        }
    }
}

class TestStoreService:
    """Test cases for the StoreService class."""

    def test_singleton_pattern(self):
        """Test that StoreService follows singleton pattern."""
        # Reset the singleton for testing
        StoreService._instance = None
        StoreService._initialized = False
        
        # First instance
        service1 = StoreService()
        assert service1 is not None
        
        # Second instance should be the same object
        service2 = StoreService()
        assert service1 is service2
        
        # But with _data parameter, we should get a new instance
        service3 = StoreService(_data={"store": {}})
        assert service3 is not service1
        
        # Cleanup
        StoreService._instance = None
        StoreService._initialized = False

    def test_load_store_data_success(self):
        """Test loading store data from a file."""
        # Mock the file operations
        mock_file = mock_open(read_data=json.dumps(SAMPLE_STORE_DATA))
        
        with patch("builtins.open", mock_file):
            service = StoreService(_data=SAMPLE_STORE_DATA["store"])
            
            # Test get_store_info
            store_info = service.get_store_info()
            assert isinstance(store_info, StoreResponse)
            assert store_info.name == "Test Store"
            assert store_info.location.city == "Test City"
            
            # Test get_store_hours
            hours = service.get_store_hours()
            assert isinstance(hours, StoreHoursResponse)
            assert hours.hours.monday_to_friday == "9:00 AM - 6:00 PM"
            
            # Test get_contact_info
            contact = service.get_contact_info()
            assert isinstance(contact, StoreContactResponse)
            assert contact.contact.email == "test@example.com"
            assert str(contact.social_media.facebook) == "https://facebook.com/teststore"
            
            # Test get_payment_methods
            payment_methods = service.get_payment_methods()
            assert isinstance(payment_methods, list)
            assert "credit_card" in payment_methods
            
            # Test get_location
            location = service.get_location()
            assert isinstance(location, dict)
            assert location["address"] == "123 Test St, Test City, 12345"

    def test_get_promotions(self):
        """Test getting promotions with active_only filter."""
        service = StoreService(_data=SAMPLE_STORE_DATA["store"])
        
        # Test with active_only=True (default)
        active_promos = service.get_promotions()
        assert isinstance(active_promos, StorePromotionsResponse)
        assert len(active_promos.promotions) == 1
        assert active_promos.promotions[0].title == "Summer Sale"
        
        # Test with active_only=False
        all_promos = service.get_promotions(active_only=False)
        assert len(all_promos.promotions) == 2
        assert any(p.title == "Expired Promo" for p in all_promos.promotions)

    def test_file_not_found(self):
        """Test handling of missing data file."""
        # Reset the singleton for testing
        StoreService._instance = None
        StoreService._initialized = False
        
        with patch("builtins.open") as mock_open:
            mock_open.side_effect = FileNotFoundError("File not found")
            with pytest.raises(RuntimeError) as exc_info:
                StoreService("/nonexistent/file.json")
            assert "Store data file not found" in str(exc_info.value)
    
    def test_invalid_json(self):
        """Test handling of invalid JSON data."""
        # Reset the singleton for testing
        StoreService._instance = None
        StoreService._initialized = False
        
        mock_file = mock_open(read_data="{invalid json")
        with patch("builtins.open", mock_file):
            with patch("json.load") as mock_json_load:
                mock_json_load.side_effect = json.JSONDecodeError("Expecting value", "{invalid json", 0)
                with pytest.raises(RuntimeError) as exc_info:
                    StoreService("/invalid.json")
                assert "Invalid JSON" in str(exc_info.value)
    
    def test_missing_data_handling(self):
        """Test handling of missing data in the store data."""
        # Test with minimal valid data
        minimal_data = {
            "store": {
                "name": "Minimal Store",
                "location": {
                    "city": "Test City",
                    "country": "Test Country",
                    "address": "123 Test St"
                },
                "contact": {
                    "email": "test@example.com",
                    "phone": "+1234567890",
                    "website": "https://example.com"
                },
                "hours": {
                    "monday_to_friday": "9-5",
                    "saturday": "10-4",
                    "sunday": "Closed"
                },
                "social_media": {}
            }
        }
        
        service = StoreService(_data=minimal_data["store"])
        
        # These should not raise exceptions
        assert isinstance(service.get_store_info(), StoreResponse)
        assert isinstance(service.get_social_media_links(), dict)
        assert isinstance(service.get_payment_methods(), list)
        
        # Test with invalid data that should raise validation errors
        invalid_data = {"store": {"name": "Invalid Store"}}
        service = StoreService(_data=invalid_data["store"])
        
        with pytest.raises(HTTPException) as exc_info:
            service.get_store_info()
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
