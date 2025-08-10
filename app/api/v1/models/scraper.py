"""
Pydantic models for scraper API
"""

from pydantic import BaseModel, HttpUrl, validator, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

class ScraperStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class ScraperType(str, Enum):
    SIMPLE = "simple"
    AI_POWERED = "ai_powered"
    CUSTOM = "custom"

class ScheduleType(str, Enum):
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM_CRON = "custom_cron"

class ScraperCreate(BaseModel):
    """Model for creating a new scraper"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    url: HttpUrl
    query: str = Field(..., min_length=1, max_length=500, description="Natural language description of what to extract")
    selectors: Optional[Dict[str, str]] = Field(default_factory=dict, description="Manual CSS selectors")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ai_enabled: bool = Field(default=True, description="Enable AI-powered extraction")
    use_browser: bool = Field(default=False, description="Force browser rendering")
    timeout: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    tags: Optional[List[str]] = Field(default_factory=list)
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return v
    
    @validator('options')
    def validate_options(cls, v):
        allowed_options = {
            'headers', 'cookies', 'proxy', 'delay', 'follow_redirects',
            'extract_links', 'extract_images', 'custom_user_agent'
        }
        if v:
            invalid_options = set(v.keys()) - allowed_options
            if invalid_options:
                raise ValueError(f"Invalid options: {invalid_options}")
        return v

class ScraperUpdate(BaseModel):
    """Model for updating a scraper"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    url: Optional[HttpUrl] = None
    query: Optional[str] = Field(None, min_length=1, max_length=500)
    selectors: Optional[Dict[str, str]] = None
    options: Optional[Dict[str, Any]] = None
    ai_enabled: Optional[bool] = None
    use_browser: Optional[bool] = None
    timeout: Optional[int] = Field(None, ge=5, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    tags: Optional[List[str]] = None
    status: Optional[ScraperStatus] = None

class ScraperResponse(BaseModel):
    """Response model for scraper details"""
    id: str
    name: str
    description: Optional[str]
    url: str
    query: str
    selectors: Dict[str, str]
    options: Dict[str, Any]
    ai_enabled: bool
    use_browser: bool
    timeout: int
    max_retries: int
    tags: List[str]
    status: ScraperStatus
    scraper_type: ScraperType
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime]
    total_runs: int
    success_rate: float
    avg_execution_time: float
    user_id: str
    
    class Config:
        from_attributes = True

class ScrapersList(BaseModel):
    """Response model for scrapers list"""
    scrapers: List[ScraperResponse]
    total: int
    page: int
    per_page: int
    has_next: bool

class ScraperRun(BaseModel):
    """Model for running a scraper"""
    variables: Optional[Dict[str, str]] = Field(default_factory=dict, description="Runtime variables for URL/selector substitution")
    options_override: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Override scraper options for this run")
    async_execution: bool = Field(default=False, description="Run in background")
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook URL for async results")
    save_html: bool = Field(default=False, description="Save source HTML")
    
    @validator('variables')
    def validate_variables(cls, v):
        if v and len(str(v)) > 5000:
            raise ValueError("Variables too large")
        return v

class ScraperRunResponse(BaseModel):
    """Response model for scraper execution"""
    run_id: str
    status: str  # running, completed, failed
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    execution_time: Optional[float] = None
    message: Optional[str] = None

class ScraperRunDetails(BaseModel):
    """Detailed run information"""
    id: str
    scraper_id: str
    status: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    errors: List[str]
    execution_time: float
    created_at: datetime
    completed_at: Optional[datetime]
    variables_used: Dict[str, str]
    selectors_used: Dict[str, str]
    source_html_size: int
    data_points_extracted: int
    
    class Config:
        from_attributes = True

class ScraperSchedule(BaseModel):
    """Model for scraper scheduling"""
    schedule_type: ScheduleType
    cron_expression: Optional[str] = Field(None, description="Cron expression for custom scheduling")
    timezone: str = Field(default="UTC")
    variables: Optional[Dict[str, str]] = Field(default_factory=dict)
    webhook_url: Optional[HttpUrl] = None
    enabled: bool = Field(default=True)
    max_runs: Optional[int] = Field(None, ge=1, description="Maximum number of runs (null for unlimited)")
    
    @validator('cron_expression')
    def validate_cron(cls, v, values):
        if values.get('schedule_type') == ScheduleType.CUSTOM_CRON and not v:
            raise ValueError("Cron expression required for custom scheduling")
        return v

class ScraperScheduleResponse(BaseModel):
    """Response model for scraper schedule"""
    id: str
    scraper_id: str
    schedule_type: ScheduleType
    cron_expression: Optional[str]
    timezone: str
    variables: Dict[str, str]
    webhook_url: Optional[str]
    enabled: bool
    max_runs: Optional[int]
    runs_completed: int
    next_run_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScraperAnalytics(BaseModel):
    """Analytics data for a scraper"""
    scraper_id: str
    period_days: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    total_data_points: int
    avg_data_points_per_run: float
    error_breakdown: Dict[str, int]
    daily_stats: List[Dict[str, Any]]
    performance_trend: str  # improving, declining, stable
    
    class Config:
        from_attributes = True

class BulkScraperCreate(BaseModel):
    """Model for creating multiple scrapers at once"""
    scrapers: List[ScraperCreate] = Field(..., max_items=50)
    default_options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('scrapers')
    def validate_scrapers_count(cls, v):
        if len(v) == 0:
            raise ValueError("At least one scraper required")
        return v

class BulkScraperResponse(BaseModel):
    """Response for bulk scraper creation"""
    created: List[ScraperResponse]
    failed: List[Dict[str, Any]]
    total_created: int
    total_failed: int

class ScraperTemplate(BaseModel):
    """Template for common scraping patterns"""
    name: str
    description: str
    category: str
    url_pattern: str
    selectors: Dict[str, str]
    options: Dict[str, Any]
    example_urls: List[str]
    tags: List[str]

class ScraperExport(BaseModel):
    """Export format for scraper configuration"""
    version: str = "1.0"
    scraper: ScraperResponse
    runs_sample: Optional[List[ScraperRunDetails]] = None
    analytics: Optional[ScraperAnalytics] = None
    export_date: datetime = Field(default_factory=datetime.utcnow)

class ScraperImport(BaseModel):
    """Import format for scraper configuration"""
    scraper: ScraperCreate
    schedule: Optional[ScraperSchedule] = None
    
class WebhookPayload(BaseModel):
    """Payload sent to webhooks"""
    event: str  # run_completed, run_failed, schedule_completed
    scraper_id: str
    run_id: str
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None
    status: str
    errors: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None