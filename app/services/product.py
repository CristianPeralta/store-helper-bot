import logging
from typing import Optional
import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.product import Product, ProductListResponse, CategoryListResponse

logger = logging.getLogger(__name__)

settings = get_settings()
FAKE_STORE_API_URL = settings.FAKE_STORE_API_URL

class ProductService:
    """Service for interacting with the FakeStore API."""
    
    def __init__(self, base_url: str = FAKE_STORE_API_URL):
        """Initialize the service with the API base URL."""
        self.base_url = base_url
        self.timeout = 10.0  # seconds
    
    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to the FakeStore API.
        
        Args:
            endpoint: The API endpoint path
            params: Optional query parameters
            
        Returns:
            The JSON response as a dictionary
            
        Raises:
            HTTPException: If there's an error with the request or response
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=self.timeout)
                
                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Product not found"
                    )
                    
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            status_code = (
                status.HTTP_404_NOT_FOUND 
                if e.response.status_code == 404 
                else status.HTTP_502_BAD_GATEWAY
            )
            detail = "Product not found" if e.response.status_code == 404 else "Error communicating with the products service"
            logger.error(f"HTTP error from FakeStore API: {e}")
            raise HTTPException(status_code=status_code, detail=detail)
            
        except httpx.RequestError as e:
            logger.error(f"Request to FakeStore API failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Products service is currently unavailable"
            )
    
    async def get_products(
        self,
        limit: int = 10,
        sort: Optional[str] = None,
        category: Optional[str] = None
    ) -> ProductListResponse:
        """
        Get a list of products with optional filtering and sorting.
        
        Args:
            limit: Maximum number of products to return
            sort: Sort order ('asc' or 'desc')
            category: Filter by category
            
        Returns:
            ProductListResponse with the list of products
        """
        endpoint = "products"
        params = {}
        
        if limit:
            params['limit'] = limit
        if sort:
            params['sort'] = sort
        
        data = await self._make_request(endpoint, params=params)
        
        # Filter by category if specified
        if category:
            data = [p for p in data if p['category'].lower() == category.lower()]
        
        # Convert to Product objects
        products = [Product(**item) for item in data]
        
        return ProductListResponse(
            products=products,
            total=len(products),
            skip=0,
            limit=len(products)
        )
    
    async def get_product(self, product_id: int) -> Product:
        """
        Get a single product by ID.
        
        Args:
            product_id: The ID of the product to retrieve
            
        Returns:
            The requested Product
            
        Raises:
            HTTPException: If the product is not found or there's an error
        """
        data = await self._make_request(f"products/{product_id}")
        return Product(**data)
    
    async def get_categories(self) -> CategoryListResponse:
        """
        Get a list of all product categories.
        
        Returns:
            CategoryListResponse with the list of categories
        """
        categories = await self._make_request("products/categories")
        return CategoryListResponse(categories=categories)
    
    async def get_products_by_category(self, category: str) -> ProductListResponse:
        """
        Get all products in a specific category.
        
        Args:
            category: The category to filter by
            
        Returns:
            ProductListResponse with the filtered products
        """
        # First get all categories to validate the requested category exists
        categories = await self.get_categories()
        if category.lower() not in [c.lower() for c in categories.categories]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{category}' not found"
            )
        
        data = await self._make_request(f"products/category/{category}")
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No products found for the given category"
            )
        
        # Convert to Product objects
        products = [Product(**item) for item in data]
        
        return ProductListResponse(
            products=products,
            total=len(products),
            skip=0,
            limit=len(products)
        )
    
    async def search_products(self, query: str) -> ProductListResponse:
        """
        Search for products by title or description.
        
        Note: The FakeStore API doesn't support search natively,
        so we implement client-side search here.
        
        Args:
            query: The search query string
            
        Returns:
            ProductListResponse with matching products
        """
        # Get all products and filter client-side
        all_products = await self.get_products(limit=100)  # Get up to 100 products
        
        # Simple case-insensitive search in title and description
        query = query.lower()
        matching_products = [
            p for p in all_products.products
            if (query in p.title.lower()) or (query in p.description.lower())
        ]
        
        return ProductListResponse(
            products=matching_products,
            total=len(matching_products),
            skip=0,
            limit=len(matching_products)
        )


# Create a singleton instance
product_service = ProductService()
