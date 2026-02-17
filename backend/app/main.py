"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import get_chat_service, get_document_service
from app.api.routes import admin_routes, auth_routes, chat_routes
from app.core.config import get_settings
from app.core.errors import MindwellException
from app.core.logging import get_logger, setup_logging
from app.db.connection import init_db

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger.info("Starting Mindwell API", environment=settings.environment)

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    # Initialize dependencies
    _ = get_chat_service()
    _ = get_document_service()
    logger.info("Services initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down Mindwell API")


# Create FastAPI application
app = FastAPI(
    title="Mindwell AI API",
    description="AI-powered cognitive behavioral therapy assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(MindwellException)
async def mindwell_exception_handler(request: Request, exc: MindwellException) -> JSONResponse:
    """Handle Mindwell exceptions."""
    logger.error(
        "Mindwell exception",
        error=exc.message,
        details=exc.details,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": exc.message, "code": exc.__class__.__name__},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Include routers
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)


# Health check endpoint
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Mindwell AI API",
        "version": "0.1.0",
        "docs": "/docs",
    }
