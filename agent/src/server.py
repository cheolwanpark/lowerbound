"""FastAPI application server."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import Settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for application startup/shutdown.

    Args:
        app: FastAPI application

    Yields:
        None
    """
    # Startup
    logger.info("Starting Crypto Portfolio Risk Advisor API")

    # Load and validate settings
    settings = Settings.from_env()
    settings.validate()

    # Store settings in app state
    app.state.settings = settings

    logger.info(f"Settings loaded: backend_url={settings.backend_api_url}")
    logger.info(f"Queue: {settings.queue_name}, Max workers: {settings.max_workers}")
    logger.info(f"Agent limits: max_turns={settings.agent_max_turns}, "
                f"timeout={settings.agent_timeout_seconds}s, "
                f"max_tool_calls={settings.agent_max_tool_calls}")

    yield

    # Shutdown
    logger.info("Shutting down Crypto Portfolio Risk Advisor API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Crypto Portfolio Risk Advisor API",
        description="AI-powered crypto portfolio risk analysis and advisory",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    app.include_router(router)

    @app.get("/")
    async def root():
        """Root endpoint for health check."""
        return {
            "service": "Crypto Portfolio Risk Advisor",
            "version": "1.0.0",
            "status": "running",
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
