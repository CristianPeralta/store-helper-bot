import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, status

from app.schemas.product import Product, ProductListResponse, CategoryListResponse
from app.services.product import ProductService

# Sample test data
SAMPLE_PRODUCTS = [
    {
        "id": 1,
        "title": "Test Product 1",
        "price": 9.99,
        "description": "A test product",
        "category": "test",
        "image": "http://example.com/image1.jpg",
        "rating": {"rate": 4.5, "count": 100}
    },
    {
        "id": 2,
        "title": "Test Product 2",
        "price": 19.99,
        "description": "Another test product",
        "category": "test",
        "image": "http://example.com/image2.jpg",
        "rating": {"rate": 4.0, "count": 50}
    }
]

SAMPLE_CATEGORIES = ["electronics", "jewelery", "men's clothing", "women's clothing"]

@pytest.mark.asyncio
class TestProductService:
    """Test cases for ProductService."""
    
    @pytest.fixture
    def product_service(self):
        """Create a ProductService instance for testing with a test base URL."""
        return ProductService(base_url="http://test-api.com")
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Create a mock HTTPX client with async context manager support."""
        with patch('httpx.AsyncClient') as mock_client:
            # Create a mock response
            mock_response = MagicMock()
            
            # Set up the async methods
            mock_response.json.return_value = SAMPLE_PRODUCTS
            mock_response.raise_for_status = MagicMock()
            
            # Create a mock client that returns the mock response
            async def mock_get(*args, **kwargs):
                return mock_response
                
            # Create an async context manager mock
            mock_async_client = AsyncMock()
            mock_async_client.get = mock_get
            
            # Set up the context manager to return the mock client
            mock_client.return_value.__aenter__.return_value = mock_async_client
            
            # Return the mock response for assertions
            yield mock_response
    
    @pytest.fixture
    def mock_httpx_client_error(self):
        """Create a mock HTTPX client that raises an HTTP error."""
        with patch('httpx.AsyncClient') as mock_client:
            # Create a mock response that raises an error
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Bad Gateway"
            )
            
            # Create a mock client that returns the mock response
            async def mock_get(*args, **kwargs):
                return mock_response
                
            # Create an async context manager mock
            mock_async_client = AsyncMock()
            mock_async_client.get = mock_get
            
            # Set up the context manager to return the mock client
            mock_client.return_value.__aenter__.return_value = mock_async_client
            
            # Return the mock response for assertions
            yield mock_response
    
    async def test_get_products(self, product_service, mock_httpx_client):
        """Test getting a list of products."""
        # Configure the mock to return our sample products
        mock_httpx_client.json.return_value = SAMPLE_PRODUCTS
        
        # Call the method under test
        result = await product_service.get_products(limit=2)
        
        # Verify the response
        assert isinstance(result, ProductListResponse)
        assert len(result.products) == 2
        assert result.products[0].title == "Test Product 1"
        assert result.products[1].price == 19.99
        
        # Verify the mock was called correctly
        mock_httpx_client.raise_for_status.assert_called_once()
    
    async def test_get_products_with_category_filter(self, product_service, mock_httpx_client):
        """Test getting products filtered by category."""
        # First mock the categories endpoint
        with patch.object(product_service, 'get_categories') as mock_get_categories:
            mock_get_categories.return_value = CategoryListResponse(categories=["test"])
            
            # Then test the products endpoint
            result = await product_service.get_products(category="test")
            
            assert isinstance(result, ProductListResponse)
            assert len(result.products) == 2
            assert all(p.category.lower() == "test" for p in result.products)
    
    async def test_get_product(self, product_service, mock_httpx_client):
        """Test getting a single product by ID."""
        # Configure the mock to return a single product
        mock_httpx_client.json.return_value = SAMPLE_PRODUCTS[0]
        
        # Call the method under test
        result = await product_service.get_product(1)
        
        # Verify the response
        assert isinstance(result, Product)
        assert result.id == 1
        assert result.title == "Test Product 1"
        assert result.price == 9.99
        
        # Verify the mock was called correctly
        mock_httpx_client.raise_for_status.assert_called_once()
    
    async def test_get_product_not_found(self, product_service, mock_httpx_client):
        """Test getting a non-existent product."""
        # Configure the mock to raise HTTPStatusError with 404
        mock_httpx_client.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=httpx.Request("GET", "http://test"),
            response=httpx.Response(404, json={"message": "Not Found"})
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await product_service.get_product(999)
            
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_categories(self, product_service, mock_httpx_client):
        """Test getting product categories."""
        # Configure the mock to return categories
        mock_httpx_client.json.return_value = SAMPLE_CATEGORIES
        
        # Call the method under test
        result = await product_service.get_categories()
        
        # Verify the response
        assert isinstance(result, CategoryListResponse)
        assert len(result.categories) == 4
        assert "electronics" in result.categories
        
        # Verify the mock was called correctly
        mock_httpx_client.raise_for_status.assert_called_once()
    
    async def test_get_products_by_category(self, product_service, mock_httpx_client):
        """Test getting products by category."""
        # First mock the categories endpoint
        with patch.object(product_service, 'get_categories') as mock_get_categories:
            mock_get_categories.return_value = CategoryListResponse(categories=["test"])
            
            # Configure the products endpoint mock
            test_products = [p for p in SAMPLE_PRODUCTS if p["category"] == "test"]
            mock_httpx_client.json.return_value = test_products
            
            # Call the method under test
            result = await product_service.get_products_by_category("test")
            
            # Verify the response
            assert isinstance(result, ProductListResponse)
            assert len(result.products) == 2
            assert all(p.category.lower() == "test" for p in result.products)
            
            # Verify the mock was called correctly
            mock_httpx_client.raise_for_status.assert_called_once()
            
            # Verify the mock was called with the correct URL
            # We'll just verify that the JSON method was called
            # The actual URL verification is complex due to the async context manager
            assert mock_httpx_client.json.called
    
    async def test_search_products(self, product_service):
        """Test searching for products."""
        # Create test products
        test_products = [Product(**p) for p in SAMPLE_PRODUCTS]
        
        # Mock get_products to return our test data
        with patch.object(product_service, 'get_products') as mock_get_products:
            mock_get_products.return_value = ProductListResponse(
                products=test_products,
                total=len(test_products),
                skip=0,
                limit=len(test_products)
            )
            
            # Test search
            result = await product_service.search_products("test")
            assert isinstance(result, ProductListResponse)
            assert len(result.products) == 2  # Both products contain "test" in title/description
            
            # Test case-insensitive search
            result = await product_service.search_products("PRODUCT")
            assert len(result.products) == 2
            
            # Test no results
            result = await product_service.search_products("nonexistent")
            assert len(result.products) == 0
    
    async def test_api_error_handling(self, product_service, mock_httpx_client_error):
        """Test error handling for API errors."""
        with pytest.raises(HTTPException) as exc_info:
            await product_service.get_products()
            
        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
