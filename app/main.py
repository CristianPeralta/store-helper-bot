from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat
from app.db import database
from app.core import get_settings, logger

# Initialize settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application."""
    # Startup
    logger.info("Starting application...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Initialize database
    try:
        # Create all database tables
        await database.create_all()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await database.close()  # Properly close database connections

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Store Helper Bot API",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(chat.router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint to check if the API is running."""
    return {
        "message": f"{settings.APP_NAME} API is running",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
