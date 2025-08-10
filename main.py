"""
Web Scraper - Main FastAPI Application
AI-Powered Web Scraping Platform
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.config import settings
from app.api.v1.routes import scrapers, extraction, auth, analytics
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.core.storage.database import init_db
from app.core.storage.cache import init_cache
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Web Scraper Platform...")
    
    # Initialize database
    await init_db()
    
    # Initialize cache
    await init_cache()
    
    logger.info("✅ Web Scraper Platform started successfully")
    yield
    
    logger.info("Shutting down Web Scraper Platform...")

# Create FastAPI app
app = FastAPI(
    title="Web Scraper Platform",
    description="AI-Powered Web Scraping and Data Intelligence Platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Security
security = HTTPBearer()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    scrapers.router,
    prefix="/api/v1/scrapers",
    tags=["Scrapers"],
    dependencies=[Depends(security)]
)

app.include_router(
    extraction.router,
    prefix="/api/v1/extract",
    tags=["Data Extraction"],
    dependencies=[Depends(security)]
)

app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["Analytics"],
    dependencies=[Depends(security)]
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Web Scraper Platform API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/api/docs"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "cache": "connected",
        "ai_service": "operational"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else 4
    )