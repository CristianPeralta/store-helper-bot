"""Unit tests for StoreService."""
import json
from datetime import date, timedelta
from unittest.mock import patch, mock_open

import pytest

from app.schemas.store import (
    StoreResponse,
    StoreHoursResponse,
    StoreContactResponse,
    StorePromotionsResponse,
)
from app.services.store import StoreService

# Sample store data for testing (matches the actual store.json structure)
SAMPLE_STORE_DATA = {
    "name": "Fake Store",
    "location": {
        "city": "Lima",
        "country": "Peru",
        "address": "123 Fake Avenue, Miraflores"
    },
    "contact": {
        "phone": "+51 987 654 321",
        "email": "contact@fakestore.com",
        "website": "https://www.fakestore.com"
    },
    "hours": {
        "monday_to_friday": "9:00 AM - 8:00 PM",
        "saturday": "10:00 AM - 6:00 PM",
        "sunday": "Closed"
    },
    "promotions": [
        {
            "title": "Buy one, get one free on basic t-shirts",
            "valid_until": (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        },
        {
            "title": "20% off on electronics",
            "valid_until": (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")  # Expired
        }
    ],
    "payment_methods": [
        "Cash",
        "Credit card",
        "Yape",
        "Plin"
    ],
    "social_media": {
        "facebook": "https://facebook.com/fakestore",
        "instagram": "https://instagram.com/fakestore",
        "tiktok": "https://tiktok.com/@fakestore"
    }
}


@pytest.fixture
def mock_store_data():
    """Return sample store data as a dictionary."""
    return SAMPLE_STORE_DATA.copy()


@pytest.fixture
def store_service(mock_store_data):
    """Create a StoreService instance with test data."""
    # Clear any existing singleton instance
    StoreService._instance = None
    StoreService._initialized = False
    
    # Create a new instance with test data directly
    service = StoreService(_data=mock_store_data)
    return service


class TestStoreService:
    """Test cases for StoreService."""

    def test_init_default_data_file(self):
        """Test initialization with default data file path."""
        # Clear singleton
        StoreService._instance = None
        StoreService._initialized = False
        
        with patch('builtins.open', mock_open(read_data='{"store": {}}')) as mock_file:
            with patch('pathlib.Path.exists', return_value=True):
                service = StoreService()
                assert "data/store.json" in str(service.data_file).replace("\\", "/")

    def test_init_custom_data_file(self, tmp_path):
        """Test initialization with custom data file path."""
        # Clear singleton
        StoreService._instance = None
        StoreService._initialized = False
        
        test_file = tmp_path / "custom_store.json"
        test_file.write_text('{"store": {}}')
        
        with patch('builtins.open', mock_open(read_data='{"store": {}}')) as mock_file:
            with patch('pathlib.Path.exists', return_value=True):
                service = StoreService(str(test_file))
                assert service.data_file == test_file

    def test_init_file_not_found(self):
        """Test initialization with non-existent file."""
        # Clear any existing instance
        StoreService._instance = None
        StoreService._initialized = False
        
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            with patch('pathlib.Path.exists', return_value=False):
                with pytest.raises(RuntimeError, match="Store data file not found"):
                    StoreService("nonexistent.json")

    def test_init_invalid_json(self, tmp_path):
        """Test initialization with invalid JSON data."""
        # Clear any existing instance
        StoreService._instance = None
        StoreService._initialized = False
        
        test_file = tmp_path / "invalid.json"
        test_file.write_text('{invalid json}')
        
        # Mock the file operations to raise a JSONDecodeError
        def mock_json_load(*args, **kwargs):
            raise json.JSONDecodeError("Expecting property name enclosed in double quotes", "{invalid json}", 1)
            
        with patch('builtins.open', mock_open(read_data='{invalid json}')) as mock_file:
            with patch('pathlib.Path.exists', return_value=True):
                with patch('json.load', side_effect=mock_json_load):
                    with pytest.raises(RuntimeError, match="Invalid JSON"):
                        StoreService(str(test_file))

    def test_get_store_info(self, store_service, mock_store_data):
        """Test getting complete store information."""
        result = store_service.get_store_info()
        assert isinstance(result, StoreResponse)
        assert result.name == mock_store_data["name"]
        # Convert Pydantic model to dict and check the relevant fields
        location_dict = result.location.model_dump()
        assert location_dict["city"] == mock_store_data["location"]["city"]
        assert location_dict["country"] == mock_store_data["location"]["country"]
        assert location_dict["address"] == mock_store_data["location"]["address"]

    def test_get_store_hours(self, store_service, mock_store_data):
        """Test getting store hours."""
        result = store_service.get_store_hours()
        assert isinstance(result, StoreHoursResponse)
        # Convert Pydantic model to dict and check the relevant fields
        hours_dict = result.hours.model_dump()
        assert hours_dict["monday_to_friday"] == mock_store_data["hours"]["monday_to_friday"]
        assert hours_dict["saturday"] == mock_store_data["hours"]["saturday"]
        assert hours_dict["sunday"] == mock_store_data["hours"]["sunday"]

    def test_get_contact_info(self, store_service, mock_store_data):
        """Test getting contact information."""
        result = store_service.get_contact_info()
        assert isinstance(result, StoreContactResponse)
        
        # Convert Pydantic model to dict and check the relevant fields
        contact_dict = result.contact.model_dump()
        assert contact_dict["phone"] == mock_store_data["contact"]["phone"]
        assert contact_dict["email"] == mock_store_data["contact"]["email"]
        # Handle potential trailing slash in URL
        website = str(contact_dict["website"]).rstrip('/')
        expected_website = mock_store_data["contact"]["website"].rstrip('/')
        assert website == expected_website
        
        # Check social media - compare individual fields to handle URL variations
        social_media = result.social_media.model_dump()
        for key, value in mock_store_data["social_media"].items():
            assert key in social_media, f"Missing social media key: {key}"
            # Normalize URLs for comparison
            expected_url = str(value).rstrip('/')
            actual_url = str(social_media[key]).rstrip('/')
            assert actual_url == expected_url, f"Mismatch for {key}: expected {expected_url}, got {actual_url}"

    def test_get_promotions_all(self, store_service, mock_store_data):
        """Test getting all promotions (including expired)."""
        result = store_service.get_promotions(active_only=False)
        assert isinstance(result, StorePromotionsResponse)
        assert len(result.promotions) == 2

    def test_get_promotions_active_only(self):
        """Test getting only active promotions."""
        # Create test data with one active and one expired promotion
        today = date.today()
        active_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        expired_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        test_data = {
            "name": "Test Store",
            "location": {"city": "Test", "country": "Test", "address": "Test"},
            "hours": {"monday_to_friday": "", "saturday": "", "sunday": ""},
            "contact": {"phone": "", "email": "", "website": ""},
            "social_media": {},
            "payment_methods": [],
            "promotions": [
                {
                    "title": "Active Promotion",
                    "valid_until": active_date
                },
                {
                    "title": "Expired Promotion",
                    "valid_until": expired_date
                }
            ]
        }
        
        # Create a new service instance with test data directly
        StoreService._instance = None
        StoreService._initialized = False
        service = StoreService(_data=test_data)
        
        # Test active_only=True (should only return active promotions)
        result = service.get_promotions(active_only=True)
        assert isinstance(result, StorePromotionsResponse)
        assert len(result.promotions) == 1, f"Expected 1 active promotion, got {len(result.promotions)}"
        assert result.promotions[0].title == "Active Promotion"
        
        # Test active_only=False (should return all promotions)
        result = service.get_promotions(active_only=False)
        assert len(result.promotions) == 2, f"Expected 2 promotions, got {len(result.promotions)}"

    def test_get_payment_methods(self, store_service, mock_store_data):
        """Test getting payment methods."""
        result = store_service.get_payment_methods()
        assert isinstance(result, list)
        assert result == mock_store_data["payment_methods"]

    def test_get_social_media_links(self, store_service, mock_store_data):
        """Test getting social media links."""
        result = store_service.get_social_media_links()
        assert isinstance(result, dict)
        assert result == mock_store_data["social_media"]

    def test_get_location(self, store_service, mock_store_data):
        """Test getting store location."""
        result = store_service.get_location()
        assert isinstance(result, dict)
        assert result == mock_store_data["location"]

    def test_minimal_data_handling(self):
        """Test handling of minimal required data in the store data."""
        # Create a minimal store data with all required fields and valid values
        minimal_store_data = {
            "name": "Minimal Store",
            "location": {
                "city": "Test City",
                "country": "Test Country",
                "address": "123 Test St"
            },
            "hours": {
                "monday_to_friday": "9:00 AM - 5:00 PM",
                "saturday": "10:00 AM - 4:00 PM",
                "sunday": "Closed"
            },
            "contact": {
                "phone": "+1-555-123-4567",  # Must be a valid phone number
                "email": "test@example.com",  # Must be a valid email
                "website": "https://example.com"  # Must be a valid URL
            },
            "social_media": {},
            "payment_methods": [],
            "promotions": []
        }
        
        # Create a new service instance with test data directly
        StoreService._instance = None
        StoreService._initialized = False
        service = StoreService(_data=minimal_store_data)
        
        # Test that we can retrieve all the basic info
        result = service.get_store_info()
        assert isinstance(result, StoreResponse)
        assert result.name == "Minimal Store"
        
        # Test store hours
        result = service.get_store_hours()
        assert isinstance(result, StoreHoursResponse)
        assert result.hours.monday_to_friday == "9:00 AM - 5:00 PM"
        assert result.hours.saturday == "10:00 AM - 4:00 PM"
        assert result.hours.sunday == "Closed"
        
        # Test contact info
        result = service.get_contact_info()
        assert isinstance(result, StoreContactResponse)
        assert result.contact.phone == "+1-555-123-4567"
        assert result.contact.email == "test@example.com"
        # Handle potential trailing slash in URL
        website = str(result.contact.website).rstrip('/')
        assert website == "https://example.com"
        
        # Test empty collections
        result = service.get_promotions()
        assert isinstance(result, StorePromotionsResponse)
        assert result.promotions == []
        
        result = service.get_payment_methods()
        assert result == []
        
        result = service.get_social_media_links()
        assert result == {}
        
        # Test location
        result = service.get_location()
        assert isinstance(result, dict)
        assert result["city"] == "Test City"
        assert result["country"] == "Test Country"
        assert result["address"] == "123 Test St"
    
    def test_invalid_data_handling(self):
        """Test that the service handles invalid data formats gracefully."""
        # This test is now covered by test_init_invalid_json
        pass

    def test_singleton_instance(self):
        """Test that the store_service instance is a singleton."""
        # Clear any existing instance
        StoreService._instance = None
        StoreService._initialized = False
        
        # Create valid test data with all required fields
        test_data = {
            "name": "Test Store",
            "location": {
                "city": "Test City",
                "country": "Test Country",
                "address": "123 Test St"
            },
            "hours": {
                "monday_to_friday": "9:00 AM - 5:00 PM",
                "saturday": "10:00 AM - 4:00 PM",
                "sunday": "Closed"
            },
            "contact": {
                "phone": "123-456-7890",
                "email": "test@example.com",
                "website": "https://example.com"
            },
            "social_media": {},
            "payment_methods": [],
            "promotions": []
        }
        
        # Create first instance
        service1 = StoreService(_data=test_data)
        
        # Create second instance - should return the same instance
        service2 = StoreService()
        
        # Verify they are the same instance
        assert service1 is service2
        
        # Verify the data is the same
        assert service1.get_store_info().name == "Test Store"
        assert service2.get_store_info().name == "Test Store"
        
        # Create new test data for the third instance
        new_test_data = test_data.copy()
        new_test_data["name"] = "Another Store"
        
        # Verify creating with _data parameter overrides singleton behavior
        service3 = StoreService(_data=new_test_data)
        assert service3 is not service1
        assert service3.get_store_info().name == "Another Store"
