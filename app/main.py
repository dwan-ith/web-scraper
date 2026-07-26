"""
Web Scraper - Main FastAPI Application
Network-Layer API Reverse Engineering Platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.config import settings
from app.api.v1.routes import scrapers
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.rate_limit import RateLimitMiddleware
from app.core.storage.database import init_db
from app.core.storage.cache import init_cache
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HAR Reverse Engineering Platform...")
    await init_db()
    await init_cache()
    logger.info("✅ Platform started successfully")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="HAR Reverse Engineering Platform",
    description="Upload a .HAR network log → get a permanent sub-second REST API. Powered by LLM structured outputs.",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(scrapers.router, prefix="/api/v1/scrapers", tags=["Scrapers"])

@app.get("/")
async def root():
    return {"name": "HAR Reverse Engineering Platform", "version": "2.0.0", "docs": "/api/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
