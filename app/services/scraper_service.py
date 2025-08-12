"""
Scraper Service - Business Logic Layer
Handles scraper CRUD operations and execution orchestration
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from app.core.scraper.engine import ScrapingEngine, ScrapingContext, BatchScrapingEngine
from app.core.ai.analyzer import SiteAnalyzer
from app.core.storage.database import get_database
from app.core.storage.cache import get_cache
from app.utils.exceptions import ScraperNotFoundException, ValidationException
from app.config import settings

logger = logging.getLogger(__name__)

class ScraperService:
    """
    Main service for managing scrapers and executing scraping operations
    """
    
    def __init__(self):
        self.scraping_engine = ScrapingEngine()
        self.batch_engine = BatchScrapingEngine()
        self.site_analyzer = SiteAnalyzer()
        self.db = None
        self.cache = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize async components"""
        if not self._initialized:
            self.db = await get_database()
            self.cache = await get_cache()
            await self.scraping_engine.initialize()
            await self.batch_engine.initialize()
            self._initialized = True
    
    async def cleanup(self):
        """Cleanup resources"""
        if self._initialized:
            await self.scraping_engine.cleanup()
            await self.batch_engine.cleanup()
    
    async def create_scraper(
        self,
        user_id: str,
        url: str,
        name: str,
        description: str,
        user_query: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new scraper with AI-powered analysis
        """
        await self.initialize()
        
        try:
            scraper_id = str(uuid.uuid4())
            
            logger.info(f"Creating scraper {scraper_id} for user {user_id}")
            
            # Step 1: Analyze the target website
            logger.info("Analyzing website structure...")
            analysis_result = await self.site_analyzer.analyze_page("", user_query)
            
            # For now, we'll create a placeholder analysis
            # In a real implementation, we'd fetch the URL first
            selectors = self._generate_initial_selectors(user_query)
            
            # Step 2: Store scraper in database
            scraper_data = {
                'id': scraper_id,
                'user_id': user_id,
                'name': name,
                'description': description,
                'url': url,
                'user_query': user_query,
                'selectors': json.dumps(selectors),
                'options': json.dumps(options),
                'status': 'active',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            # Simulate database insert (replace with actual DB operations)
            await self._store_scraper(scraper_data)
            
            # Step 3: Cache the scraper
            cache_key = f"scraper:{scraper_id}"
            await self.cache.set(cache_key, json.dumps(scraper_data), ttl=3600)
            
            logger.info(f"Successfully created scraper {scraper_id}")
            
            return {
                'id': scraper_id,
                'name': name,
                'description': description,
                'url': url,
                'status': 'active',
                'selectors': selectors,
                'created_at': scraper_data['created_at'],
                'updated_at': scraper_data['updated_at']
            }
            
        except Exception as e:
            logger.error(f"Failed to create scraper: {e}")
            raise ValidationException(f"Failed to create scraper: {e}")
    
    def _generate_initial_selectors(self, user_query: str) -> Dict[str, str]:
        """Generate initial selectors based on user query"""
        
        query_lower = user_query.lower()
        selectors = {}
        
        # Basic heuristics for common extraction patterns
        if any(word in query_lower for word in ['title', 'heading', 'name']):
            selectors['title'] = 'h1, .title, .heading'
        
        if any(word in query_lower for word in ['price', 'cost', 'amount']):
            selectors['price'] = '.price, [class*="price"], [data-price]'
        
        if any(word in query_lower for word in ['description', 'content', 'text']):
            selectors['description'] = '.description, .content, p'
        
        if any(word in query_lower for word in ['link', 'url']):
            selectors['links'] = 'a[href]'
        
        if any(word in query_lower for word in ['image', 'photo']):
            selectors['images'] = 'img[src]'
        
        # Default fallback
        if not selectors:
            selectors = {
                'content': 'main, .main, .content',
                'links': 'a[href]'
            }
        
        return selectors
    
    async def _store_scraper(self, scraper_data: Dict[str, Any]):
        """Store scraper in database (placeholder implementation)"""
        # In a real implementation, this would use SQLAlchemy or similar
        # For now, we'll simulate database storage
        logger.info(f"Storing scraper {scraper_data['id']} in database")
        pass
    
    async def get_scraper(self, scraper_id: str, user_id: str) -> Dict[str, Any]:
        """Get a scraper by ID"""
        await self.initialize()
        
        # Try cache first
        cache_key = f"scraper:{scraper_id}"
        cached = await self.cache.get(cache_key)
        
        if cached:
            scraper_data = json.loads(cached)
            if scraper_data['user_id'] != user_id:
                raise ScraperNotFoundException(f"Scraper {scraper_id} not found")
            
            return {
                'id': scraper_data['id'],
                'name': scraper_data['name'],
                'description': scraper_data['description'],
                'url': scraper_data['url'],
                'status': scraper_data['status'],
                'selectors': json.loads(scraper_data['selectors']),
                'created_at': scraper_data['created_at'],
                'updated_at': scraper_data['updated_at']
            }
        
        # Fallback to database
        # Placeholder implementation
        raise ScraperNotFoundException(f"Scraper {scraper_id} not found")
    
    async def list_scrapers(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """List user's scrapers with pagination"""
        await self.initialize()
        
        # Placeholder implementation - would query database
        # For demo, return empty list
        return {
            'scrapers': [],
            'total': 0,
            'pages': 0
        }
    
    async def execute_scraper(
        self,
        scraper_id: str,
        user_id: str,
        variables: Dict[str, Any] = None,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute a scraper synchronously"""
        await self.initialize()
        
        try:
            # Get scraper configuration
            scraper = await self.get_scraper(scraper_id, user_id)
            
            # Prepare scraping context
            context = ScrapingContext(
                url=scraper['url'],
                user_query="",  # Could be stored in scraper
                selectors=scraper['selectors'],
                variables=variables or {},
                options=options or {}
            )
            
            # Execute scraping
            logger.info(f"Executing scraper {scraper_id}")
            result = await self.scraping_engine.scrape(context)
            
            # Store execution record
            execution_data = {
                'scraper_id': scraper_id,
                'user_id': user_id,
                'success': result.success,
                'data': result.data,
                'metadata': result.metadata,
                'execution_time': result.execution_time,
                'executed_at': datetime.utcnow()
            }
            
            await self._store_execution(execution_data)
            
            if not result.success:
                raise Exception("; ".join(result.errors))
            
            return {
                'data': result.data,
                'metadata': {
                    'execution_time': result.execution_time,
                    'elements_extracted': len(result.data),
                    'success_rate': 1.0 if result.success else 0.0,
                    'strategy_used': result.metadata.get('strategy', 'unknown'),
                    'retries': result.metadata.get('retries', 0),
                    'pages_scraped': 1,
                    'cache_hit': False,
                    'data_quality_score': self._calculate_data_quality(result.data)
                }
            }
            
        except Exception as e:
            logger.error(f"Scraper execution failed for {scraper_id}: {e}")
            
            # Store failed execution
            execution_data = {
                'scraper_id': scraper_id,
                'user_id': user_id,
                'success': False,
                'error': str(e),
                'executed_at': datetime.utcnow()
            }
            await self._store_execution(execution_data)
            
            raise
    
    async def execute_scraper_async(
        self,
        scraper_id: str,
        execution_id: str,
        user_id: str,
        variables: Dict[str, Any] = None,
        options: Dict[str, Any] = None
    ):
        """Execute a scraper asynchronously (background task)"""
        
        try:
            # Store initial execution status
            await self._store_execution_status(execution_id, 'running')
            
            # Execute scraper
            result = await self.execute_scraper(scraper_id, user_id, variables, options)
            
            # Update execution status with results
            await self._store_execution_status(
                execution_id, 
                'completed',
                data=result['data'],
                metadata=result['metadata']
            )
            
        except Exception as e:
            logger.error(f"Async scraper execution failed: {e}")
            await self._store_execution_status(
                execution_id, 
                'failed',
                error=str(e)
            )
    
    async def test_scraper(
        self,
        scraper_id: str,
        user_id: str,
        variables: Dict[str, Any] = None,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Test a scraper without storing results"""
        
        # Similar to execute_scraper but doesn't store execution records
        scraper = await self.get_scraper(scraper_id, user_id)
        
        context = ScrapingContext(
            url=scraper['url'],
            selectors=scraper['selectors'],
            variables=variables or {},
            options=options or {}
        )
        
        result = await self.scraping_engine.scrape(context)
        
        return {
            'data': result.data,
            'metadata': {
                'execution_time': result.execution_time,
                'elements_extracted': len(result.data),
                'success_rate': 1.0 if result.success else 0.0,
                'strategy_used': result.metadata.get('strategy', 'unknown'),
                'retries': result.metadata.get('retries', 0),
                'pages_scraped': 1,
                'cache_hit': False,
                'data_quality_score': self._calculate_data_quality(result.data)
            }
        }
    
    async def update_scraper(
        self,
        scraper_id: str,
        user_id: str,
        name: str = None,
        description: str = None,
        url: str = None,
        user_query: str = None,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Update an existing scraper"""
        
        # Get existing scraper
        scraper = await self.get_scraper(scraper_id, user_id)
        
        # Update fields
        updated_data = {
            'id': scraper_id,
            'name': name or scraper['name'],
            'description': description or scraper['description'],
            'url': url or scraper['url'],
            'status': scraper['status'],
            'selectors': scraper['selectors'],
            'updated_at': datetime.utcnow()
        }
        
        # Re-analyze if URL or query changed
        if url != scraper['url'] or user_query:
            new_selectors = self._generate_initial_selectors(user_query or "")
            updated_data['selectors'] = new_selectors
        
        # Update cache
        cache_key = f"scraper:{scraper_id}"
        await self.cache.set(cache_key, json.dumps(updated_data), ttl=3600)
        
        return updated_data
    
    async def delete_scraper(self, scraper_id: str, user_id: str):
        """Delete a scraper"""
        
        # Verify ownership
        await self.get_scraper(scraper_id, user_id)
        
        # Remove from cache
        cache_key = f"scraper:{scraper_id}"
        await self.cache.delete(cache_key)
        
        # Remove from database (placeholder)
        logger.info(f"Deleted scraper {scraper_id}")
    
    async def get_execution_status(
        self, 
        execution_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Get the status of an async execution"""
        
        cache_key = f"execution:{execution_id}"
        status_data = await self.cache.get(cache_key)
        
        if not status_data:
            return {'status': 'not_found'}
        
        return json.loads(status_data)
    
    async def schedule_scraper(
        self,
        scraper_id: str,
        user_id: str,
        schedule_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Schedule a scraper to run periodically"""
        
        # Verify scraper exists
        await self.get_scraper(scraper_id, user_id)
        
        schedule_id = str(uuid.uuid4())
        
        # Store schedule configuration
        schedule_data = {
            'id': schedule_id,
            'scraper_id': scraper_id,
            'user_id': user_id,
            'cron': schedule_config.get('cron', '0 0 * * *'),
            'enabled': schedule_config.get('enabled', True),
            'variables': schedule_config.get('variables', {}),
            'webhook': schedule_config.get('notification_webhook'),
            'created_at': datetime.utcnow(),
            'next_run': self._calculate_next_run(schedule_config.get('cron', '0 0 * * *'))
        }
        
        # Store in cache/database
        cache_key = f"schedule:{schedule_id}"
        await self.cache.set(cache_key, json.dumps(schedule_data, default=str), ttl=86400)
        
        logger.info(f"Scheduled scraper {scraper_id} with schedule {schedule_id}")
        
        return schedule_data
    
    async def get_scraper_history(
        self,
        scraper_id: str,
        user_id: str,
        page: int = 1,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get execution history for a scraper"""
        
        # Verify scraper access
        await self.get_scraper(scraper_id, user_id)
        
        # Placeholder - would query execution history from database
        return {
            'executions': [],
            'total': 0,
            'pages': 0
        }
    
    async def clone_scraper(
        self,
        scraper_id: str,
        user_id: str,
        clone_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Clone an existing scraper"""
        
        # Get original scraper
        original = await self.get_scraper(scraper_id, user_id)
        
        # Create new scraper with cloned configuration
        cloned_scraper = await self.create_scraper(
            user_id=user_id,
            url=clone_config.get('url', original['url']),
            name=clone_config['name'],
            description=f"Cloned from {original['name']}",
            user_query="",  # Would need to be stored/retrieved
            options={}
        )
        
        return cloned_scraper
    
    async def optimize_scraper(
        self,
        scraper_id: str,
        user_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI-powered scraper optimization"""
        
        scraper = await self.get_scraper(scraper_id, user_id)
        
        # Analyze current performance
        # This would involve looking at execution history, success rates, etc.
        
        optimization_id = str(uuid.uuid4())
        
        # Generate suggestions (placeholder)
        suggestions = [
            "Consider using more specific CSS selectors",
            "Add wait conditions for dynamic content",
            "Enable browser rendering for better compatibility"
        ]
        
        return {
            'id': optimization_id,
            'suggestions': suggestions,
            'estimated_improvement': '15-25% better accuracy',
            'auto_applied': False
        }
    
    async def get_scraper_insights(
        self,
        scraper_id: str,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get analytical insights about scraper performance"""
        
        scraper = await self.get_scraper(scraper_id, user_id)
        
        # This would analyze execution history, data quality, trends, etc.
        # Placeholder implementation
        
        return {
            'performance': {
                'success_rate': 0.95,
                'avg_execution_time': 2.3,
                'total_executions': 42,
                'data_points_extracted': 1250
            },
            'quality': {
                'completeness_score': 0.89,
                'consistency_score': 0.92,
                'freshness_score': 0.85
            },
            'trends': {
                'execution_frequency': 'increasing',
                'success_rate_trend': 'stable',
                'performance_trend': 'improving'
            },
            'anomalies': [
                {
                    'date': '2024-01-15',
                    'type': 'performance_degradation',
                    'description': 'Execution time increased by 300%'
                }
            ],
            'recommendations': [
                'Consider adding error handling for dynamic content',
                'Optimize selectors for better performance',
                'Add data validation rules'
            ]
        }
    
    async def batch_extract(
        self,
        urls: List[str],
        query: str,
        selectors: Dict[str, str] = None,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute batch extraction across multiple URLs"""
        
        await self.initialize()
        
        batch_id = str(uuid.uuid4())
        
        # Create scraping contexts for each URL
        contexts = []
        for url in urls:
            context = ScrapingContext(
                url=url,
                user_query=query,
                selectors=selectors or {},
                options=options or {}
            )
            contexts.append(context)
        
        # Execute batch scraping
        results = await self.batch_engine.scrape_batch(contexts)
        
        # Process results
        successful_results = []
        failed_count = 0
        
        for i, result in enumerate(results):
            if result.success:
                successful_results.append({
                    'url': urls[i],
                    'data': result.data,
                    'execution_time': result.execution_time
                })
            else:
                failed_count += 1
        
        return {
            'batch_id': batch_id,
            'total_urls': len(urls),
            'completed': len(successful_results),
            'failed': failed_count,
            'results': successful_results,
            'status': 'completed',
            'metadata': {
                'total_execution_time': sum(r.execution_time for r in results),
                'success_rate': len(successful_results) / len(urls)
            }
        }
    
    def _calculate_data_quality(self, data: Dict[str, Any]) -> float:
        """Calculate a quality score for extracted data"""
        
        if not data:
            return 0.0
        
        quality_score = 0.0
        total_fields = 0
        
        for field, value in data.items():
            total_fields += 1
            
            if value is None:
                continue  # Empty field
            
            if isinstance(value, str):
                if len(value.strip()) > 0:
                    quality_score += 1.0
                if len(value.strip()) > 10:  # Bonus for substantial content
                    quality_score += 0.2
            
            elif isinstance(value, (list, dict)):
                if value:  # Non-empty collection
                    quality_score += 1.0
            
            else:
                quality_score += 1.0  # Other types
        
        return min(1.0, quality_score / total_fields) if total_fields > 0 else 0.0
    
    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time from cron expression"""
        # Placeholder implementation - would use a proper cron library
        return datetime.utcnow() + timedelta(hours=24)
    
    async def _store_execution(self, execution_data: Dict[str, Any]):
        """Store execution record in database"""
        logger.info(f"Storing execution record for scraper {execution_data['scraper_id']}")
        # Placeholder - would store in database
    
    async def _store_execution_status(
        self, 
        execution_id: str, 
        status: str,
        data: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        error: str = None
    ):
        """Store execution status for async operations"""
        
        status_data = {
            'status': status,
            'data': data,
            'metadata': metadata,
            'error': error,
            'updated_at': datetime.utcnow()
        }
        
        cache_key = f"execution:{execution_id}"
        await self.cache.set(
            cache_key, 
            json.dumps(status_data, default=str), 
            ttl=86400  # Keep for 24 hours
        )