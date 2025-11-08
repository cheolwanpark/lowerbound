"""FastAPI server with async lifespan management."""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api import router
from src.config import settings
from src.database import close_pool, init_pool, init_schema, init_futures_schemas


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async lifespan context manager for FastAPI.

    Handles:
    - Database connection pool initialization/cleanup
    - Schema initialization
    """
    # Startup
    logger.info("Starting API server")
    logger.info(f"Configuration: {settings.assets_list}")

    try:
        # Initialize database
        await init_pool()
        await init_schema()
        await init_futures_schemas()
        logger.info("Database initialized (spot + futures)")

        yield

    finally:
        # Shutdown
        logger.info("Shutting down API server")
        await close_pool()
        logger.info("Database connection closed")


# Create FastAPI application
app = FastAPI(
    title="Crypto Portfolio OHLCV Service",
    description="REST API for fetching and querying cryptocurrency OHLCV data from Binance",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router, prefix="/api/v1", tags=["OHLCV"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Crypto Portfolio OHLCV Service",
        "version": "0.1.0",
        "status": "running",
        "tracked_spot_assets": settings.assets_list,
        "tracked_futures_assets": settings.futures_assets_list,
        "docs": "/docs",
        "api": "/api/v1",
    }


# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.log_level,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level=settings.log_level.lower(),
    )
