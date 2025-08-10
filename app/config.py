"""
Configuration management for Web Scraper Platform
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # App Settings
    app_name: str = "Web Scraper Platform"
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    allowed_origins: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")
    
    # Database Settings
    database_url: str = Field(env="DATABASE_URL", default="postgresql://user:pass@localhost/webscraper")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis Settings
    redis_url: str = Field(env="REDIS_URL", default="redis://localhost:6379/0")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # AI Settings
    openai_api_key: Optional[str] = Field(env="OPENAI_API_KEY", default=None)
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    anthropic_api_key: Optional[str] = Field(env="ANTHROPIC_API_KEY", default=None)
    
    # Scraping Settings
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    user_agents: List[str] = Field(default=[
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    ])
    
    # Security Settings
    secret_key: str = Field(env="SECRET_KEY", default="your-secret-key-change-this")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration: int = Field(default=3600, env="JWT_EXPIRATION")  # 1 hour
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # 1 hour
    
    # Storage Settings
    storage_type: str = Field(default="local", env="STORAGE_TYPE")  # local, s3
    aws_access_key_id: Optional[str] = Field(env="AWS_ACCESS_KEY_ID", default=None)
    aws_secret_access_key: Optional[str] = Field(env="AWS_SECRET_ACCESS_KEY", default=None)
    s3_bucket: Optional[str] = Field(env="S3_BUCKET", default=None)
    
    # Monitoring Settings
    sentry_dsn: Optional[str] = Field(env="SENTRY_DSN", default=None)
    prometheus_enabled: bool = Field(default=False, env="PROMETHEUS_ENABLED")
    
    # Celery Settings (for background tasks)
    celery_broker_url: str = Field(env="CELERY_BROKER_URL", default="redis://localhost:6379/1")
    celery_result_backend: str = Field(env="CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
    
    @validator("allowed_origins", pre=True)
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("user_agents", pre=True)
    def parse_user_agents(cls, v):
        if isinstance(v, str):
            return [ua.strip() for ua in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Environment-specific configurations
class DevelopmentSettings(Settings):
    debug: bool = True
    database_url: str = "postgresql://dev:dev@localhost/webscraper_dev"

class ProductionSettings(Settings):
    debug: bool = False
    allowed_origins: List[str] = ["https://yourdomain.com"]

class TestingSettings(Settings):
    debug: bool = True
    database_url: str = "postgresql://test:test@localhost/webscraper_test"

def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()

# Use environment-specific settings
settings = get_settings()