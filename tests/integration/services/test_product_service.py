"""Integration tests for the ProductService."""
import pytest
import httpx
from fastapi import HTTPException, status
from unittest.mock import patch, AsyncMock

from app.services.product import ProductService, product_service
from app.schemas.product import Product, ProductListResponse, CategoryListResponse

# Sample test data
SAMPLE_PRODUCTS = [
    {
        "id": 1,
        "title": "Test Product 1",
        "price": 9.99,
        "description": "A test product",
        "category": "electronics",
        "image": "http://example.com/image1.jpg",
        "rating": {"rate": 4.5, "count": 120}
    },
    {
        "id": 2,
        "title": "Test Product 2",
        "price": 19.99,
        "description": "Another test product",
        "category": "clothing",
        "image": "http://example.com/image2.jpg",
        "rating": {"rate": 4.0, "count": 85}
    }
]

SAMPLE_CATEGORIES = ["electronics", "jewelery", "men's clothing", "women's clothing"]

@pytest.mark.asyncio
class TestProductService:
    """Test cases for the ProductService class."""

    async def test_get_products_success(self, httpx_mock):
        """Test successful retrieval of products."""
        # Mock the API response with default limit parameter
        httpx_mock.add_response(
            url="https://fakestoreapi.com/products?limit=10",
            json=SAMPLE_PRODUCTS,
            status_code=200
        )
        
        # Call the service
        service = ProductService()
        result = await service.get_products()
        
        # Verify the result
        assert isinstance(result, ProductListResponse)
        assert len(result.products) == 2
        assert result.products[0].title == "Test Product 1"
        assert result.products[1].title == "Test Product 2"
        
        # Verify the request was made with the correct parameters
        request = httpx_mock.get_request()
        assert request is not None
        assert "limit=10" in str(request.url)
        assert result.total == 2

    async def test_get_products_with_filters(self, httpx_mock):
        """Test getting products with filters."""
        # Mock the API response with the correct URL pattern
        httpx_mock.add_response(
            url="https://fakestoreapi.com/products?limit=5&sort=desc",
            json=SAMPLE_PRODUCTS[:1],
            status_code=200
        )
        
        # Call the service with filters
        service = ProductService()
        result = await service.get_products(limit=5, sort="desc")
        
        # Verify the result
        assert len(result.products) == 1
        assert result.products[0].title == "Test Product 1"
        
        # Verify the request was made with the correct parameters
        request = httpx_mock.get_request()
        assert request is not None
        assert "limit=5" in str(request.url)
        assert "sort=desc" in str(request.url)

    async def test_get_product_success(self, httpx_mock):
        """Test successful retrieval of a single product."""
        # Mock the API response
        product_id = 1
        httpx_mock.add_response(
            url=f"https://fakestoreapi.com/products/{product_id}",
            json=SAMPLE_PRODUCTS[0],
            status_code=200
        )
        
        # Call the service
        service = ProductService()
        result = await service.get_product(product_id)
        
        # Verify the result
        assert isinstance(result, Product)
        assert result.id == product_id
        assert result.title == "Test Product 1"

    async def test_get_product_not_found(self, httpx_mock):
        """Test getting a non-existent product."""
        # Mock a 404 response
        product_id = 999
        httpx_mock.add_response(
            url=f"https://fakestoreapi.com/products/{product_id}",
            status_code=404,
            json={"detail": "Product not found"}
        )
        
        # Call the service and expect an exception
        service = ProductService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_product(product_id)
        
        # Verify the exception
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_categories_success(self, httpx_mock):
        """Test successful retrieval of categories."""
        # Mock the API response
        httpx_mock.add_response(
            url="https://fakestoreapi.com/products/categories",
            json=SAMPLE_CATEGORIES,
            status_code=200
        )
        
        # Call the service
        service = ProductService()
        result = await service.get_categories()
        
        # Verify the result
        assert isinstance(result, CategoryListResponse)
        assert len(result.categories) == 4
        assert "electronics" in result.categories

    async def test_get_products_by_category_success(self, httpx_mock):
        """Test getting products by category."""
        category = "electronics"
        
        # Mock the categories endpoint
        httpx_mock.add_response(
            url="https://fakestoreapi.com/products/categories",
            json=SAMPLE_CATEGORIES,
            status_code=200
        )
        
        # Mock the products by category endpoint
        httpx_mock.add_response(
            url=f"https://fakestoreapi.com/products/category/{category}",
            json=[p for p in SAMPLE_PRODUCTS if p["category"] == category],
            status_code=200
        )
        
        # Call the service
        service = ProductService()
        result = await service.get_products_by_category(category)
        
        # Verify the result
        assert isinstance(result, ProductListResponse)
        assert len(result.products) == 1
        assert result.products[0].category == category

    async def test_search_products(self, httpx_mock):
        """Test searching products."""
        # Mock the products endpoint for search
        httpx_mock.add_response(
            url="https://fakestoreapi.com/products?limit=100",
            json=SAMPLE_PRODUCTS,
            status_code=200
        )
        
        # Call the service with a search query
        service = ProductService()
        result = await service.search_products("test")
        
        # Verify the result
        assert isinstance(result, ProductListResponse)
        # Both sample products contain "test" in title/description
        assert len(result.products) == 2
        
        # Verify the request was made with the correct parameters
        request = httpx_mock.get_request()
        assert request is not None
        assert "limit=100" in str(request.url)

    async def test_http_error_handling(self, httpx_mock):
        """Test handling of HTTP errors."""
        # Mock a server error with default limit parameter
        httpx_mock.add_response(
            url="https://fakestoreapi.com/products?limit=10",
            status_code=500,
            json={"error": "Internal Server Error"}
        )
        
        # Call the service and expect an exception
        service = ProductService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_products()
        
        # Verify the exception
        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Error communicating with the products service" in str(exc_info.value.detail)

    async def test_connection_error_handling(self, httpx_mock):
        """Test handling of connection errors."""
        # Simulate a connection error
        httpx_mock.add_exception(httpx.ConnectError("Connection error"))
        
        # Call the service and expect an exception
        service = ProductService()
        with pytest.raises(HTTPException) as exc_info:
            await service.get_products()
        
        # Verify the exception
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Products service is currently unavailable" in str(exc_info.value.detail)
