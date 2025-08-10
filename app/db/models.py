"""
SQLAlchemy Database Models
Data persistence layer for the Web Scraper Platform
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scrapers = relationship("Scraper", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
    executions = relationship("ScraperExecution", back_populates="user")
    
    def __repr__(self):
        return f"<User(email='{self.email}')>"

class ApiKey(Base):
    """API keys for authentication"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<ApiKey(name='{self.name}')>"

class Scraper(Base):
    """Web scraper configuration"""
    __tablename__ = "scrapers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    url = Column(String(2048), nullable=False)
    user_query = Column(Text, nullable=False)
    selectors = Column(JSON, default=dict)  # CSS selectors as JSON
    options = Column(JSON, default=dict)    # Scraper options as JSON
    status = Column(String(50), default="active")  # active, inactive, error, analyzing
    
    # AI Analysis Results
    site_analysis = Column(JSON, default=dict)
    confidence_score = Column(Float, default=0.0)
    
    # Performance Metrics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    avg_execution_time = Column(Float, default=0.0)
    last_executed_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="scrapers")
    executions = relationship("ScraperExecution", back_populates="scraper")
    schedules = relationship("ScraperSchedule", back_populates="scraper")
    
    # Indexes
    __table_args__ = (
        Index('ix_scrapers_user_status', 'user_id', 'status'),
        Index('ix_scrapers_url', 'url'),
    )
    
    def __repr__(self):
        return f"<Scraper(name='{self.name}', url='{self.url}')>"

class ScraperExecution(Base):
    """Record of scraper execution"""
    __tablename__ = "scraper_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scraper_id = Column(UUID(as_uuid=True), ForeignKey("scrapers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Execution details
    status = Column(String(50), nullable=False)  # pending, running, completed, failed
    execution_type = Column(String(50), default="manual")  # manual, scheduled, api
    
    # Input parameters
    variables = Column(JSON, default=dict)
    options = Column(JSON, default=dict)
    
    # Results
    data = Column(JSON)  # Extracted data
    metadata = Column(JSON, default=dict)  # Execution metadata
    error_message = Column(Text)
    
    # Performance metrics
    execution_time = Column(Float)  # seconds
    pages_scraped = Column(Integer, default=1)
    elements_extracted = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    data_quality_score = Column(Float)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scraper = relationship("Scraper", back_populates="executions")
    user = relationship("User", back_populates="executions")
    
    # Indexes
    __table_args__ = (
        Index('ix_executions_scraper_status', 'scraper_id', 'status'),
        Index('ix_executions_user_created', 'user_id', 'created_at'),
        Index('ix_executions_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScraperExecution(scraper_id='{self.scraper_id}', status='{self.status}')>"

class ScraperSchedule(Base):
    """Scheduled scraper execution"""
    __tablename__ = "scraper_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scraper_id = Column(UUID(as_uuid=True), ForeignKey("scrapers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Schedule configuration
    name = Column(String(255))
    cron_expression = Column(String(100), nullable=False)
    timezone = Column(String(50), default="UTC")
    is_active = Column(Boolean, default=True)
    
    # Execution parameters
    variables = Column(JSON, default=dict)
    options = Column(JSON, default=dict)
    
    # Notification settings
    webhook_url = Column(String(2048))
    notification_events = Column(JSON, default=list)  # ["success", "failure", "start"]
    
    # Execution tracking
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    max_runs = Column(Integer)  # Optional limit
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    scraper = relationship("Scraper", back_populates="schedules")
    
    # Indexes
    __table_args__ = (
        Index('ix_schedules_next_run', 'next_run_at', 'is_active'),
        Index('ix_schedules_scraper', 'scraper_id'),
    )
    
    def __repr__(self):
        return f"<ScraperSchedule(scraper_id='{self.scraper_id}', cron='{self.cron_expression}')>"

class DataSource(Base):
    """External data sources and integrations"""
    __tablename__ = "data_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    source_type = Column(String(100), nullable=False)  # web, api, database, file
    connection_config = Column(JSON, default=dict)
    
    # Data mapping
    schema_mapping = Column(JSON, default=dict)
    transformation_rules = Column(JSON, default=dict)
    
    # Status and health
    status = Column(String(50), default="active")
    last_sync_at = Column(DateTime)
    health_check_url = Column(String(2048))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DataSource(name='{self.name}', type='{self.source_type}')>"

class DataPipeline(Base):
    """Data processing and transformation pipelines"""
    __tablename__ = "data_pipelines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Pipeline configuration
    source_scrapers = Column(JSON, default=list)  # List of scraper IDs
    processors = Column(JSON, default=list)       # Processing steps
    destinations = Column(JSON, default=list)     # Output destinations
    
    # Execution settings
    schedule = Column(String(100))  # Cron expression
    is_active = Column(Boolean, default=True)
    
    # Performance tracking
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    last_run_at = Column(DateTime)
    avg_processing_time = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DataPipeline(name='{self.name}')>"

class AlertRule(Base):
    """Monitoring and alerting rules"""
    __tablename__ = "alert_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Rule configuration
    rule_type = Column(String(100), nullable=False)  # threshold, anomaly, pattern
    target_type = Column(String(100), nullable=False)  # scraper, execution, data_quality
    target_id = Column(String(255))  # ID of the target resource
    
    # Conditions
    conditions = Column(JSON, default=dict)
    threshold_value = Column(Float)
    comparison_operator = Column(String(10))  # >, <, =, !=, etc.
    
    # Notification settings
    notification_channels = Column(JSON, default=list)  # email, webhook, slack, etc.
    notification_config = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AlertRule(name='{self.name}', type='{self.rule_type}')>"

class UsageMetrics(Base):
    """Usage tracking and analytics"""
    __tablename__ = "usage_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Metric details
    metric_type = Column(String(100), nullable=False)  # execution, api_call, data_export
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    
    # Context
    resource_type = Column(String(100))  # scraper, pipeline, etc.
    resource_id = Column(String(255))
    metadata = Column(JSON, default=dict)
    
    # Dimensions for analytics
    date_dimension = Column(String(10))  # YYYY-MM-DD
    hour_dimension = Column(Integer)     # 0-23
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for analytics queries
    __table_args__ = (
        Index('ix_metrics_user_date', 'user_id', 'date_dimension'),
        Index('ix_metrics_type_date', 'metric_type', 'date_dimension'),
        Index('ix_metrics_resource', 'resource_type', 'resource_id'),
    )
    
    def __repr__(self):
        return f"<UsageMetrics(type='{self.metric_type}', value='{self.metric_value}')>"