"""
Advanced Web Scraping Engine
AI-Powered, Multi-Strategy Scraping System
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import json
import time
from bs4 import BeautifulSoup

from app.core.scraper.browser import BrowserManager
from app.core.scraper.parser import HTMLParser
from app.core.scraper.selector import SelectorGenerator
from app.core.ai.analyzer import SiteAnalyzer
from app.core.ai.extractor import AIExtractor
from app.utils.exceptions import ScrapingException
from app.config import settings

logger = logging.getLogger(__name__)

@dataclass
class ScrapingContext:
    """Context for scraping operations"""
    url: str
    user_query: str = ""
    selectors: Dict[str, str] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    max_retries: int = 3
    timeout: int = 30
    use_browser: bool = False
    ai_enabled: bool = True

@dataclass
class ScrapingResult:
    """Result of scraping operation"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    source_html: str = ""
    selectors_used: Dict[str, str] = field(default_factory=dict)

class ScrapingEngine:
    """
    Advanced web scraping engine with multiple extraction strategies
    """
    
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.html_parser = HTMLParser()
        self.selector_generator = SelectorGenerator()
        self.site_analyzer = SiteAnalyzer()
        self.ai_extractor = AIExtractor()
        self.session = None
        
    async def initialize(self):
        """Initialize async components"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=settings.request_timeout),
            headers={
                'User-Agent': settings.user_agents[0]
            }
        )
        await self.browser_manager.initialize()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        await self.browser_manager.cleanup()
    
    async def scrape(self, context: ScrapingContext) -> ScrapingResult:
        """
        Main scraping method with multiple strategies
        """
        start_time = time.time()
        result = ScrapingResult(success=False)
        
        try:
            logger.info(f"Starting scrape for: {context.url}")
            
            # Step 1: Get HTML content
            html_content = await self._get_html_content(context)
            result.source_html = html_content
            
            # Step 2: Analyze site structure if AI enabled
            if context.ai_enabled and not context.selectors:
                analysis = await self.site_analyzer.analyze_page(
                    html_content, context.user_query
                )
                context.selectors = analysis.get('selectors', {})
                result.metadata['site_analysis'] = analysis
            
            # Step 3: Extract data using multiple strategies
            extracted_data = await self._extract_data(html_content, context)
            result.data = extracted_data
            
            # Step 4: Validate and enrich data
            if context.ai_enabled:
                enriched_data = await self.ai_extractor.enrich_data(
                    extracted_data, context.user_query
                )
                result.data = enriched_data
            
            result.success = True
            result.selectors_used = context.selectors
            
        except Exception as e:
            logger.error(f"Scraping failed for {context.url}: {str(e)}")
            result.errors.append(str(e))
            
            # Retry with different strategy
            if context.retries < context.max_retries:
                context.retries += 1
                context.use_browser = True  # Fallback to browser
                return await self.scrape(context)
        
        finally:
            result.execution_time = time.time() - start_time
            result.metadata['retries'] = context.retries
            result.metadata['strategy'] = 'browser' if context.use_browser else 'http'
        
        return result
    
    async def _get_html_content(self, context: ScrapingContext) -> str:
        """Get HTML content using appropriate method"""
        
        if context.use_browser:
            # Use browser for dynamic content
            return await self.browser_manager.get_page_content(
                context.url, 
                timeout=context.timeout
            )
        else:
            # Try HTTP request first (faster)
            try:
                async with self.session.get(context.url) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
            except Exception as e:
                logger.warning(f"HTTP request failed, falling back to browser: {e}")
                context.use_browser = True
                return await self._get_html_content(context)
    
    async def _extract_data(self, html: str, context: ScrapingContext) -> Dict[str, Any]:
        """Extract data using configured selectors"""
        
        if not context.selectors and context.user_query:
            # Generate selectors using AI
            selectors = await self.selector_generator.generate_selectors(
                html, context.user_query
            )
            context.selectors = selectors
        
        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')
        extracted_data = {}
        
        # Extract data for each selector
        for field_name, selector in context.selectors.items():
            try:
                elements = soup.select(selector)
                
                if len(elements) == 1:
                    # Single element
                    extracted_data[field_name] = self._extract_element_data(elements[0])
                elif len(elements) > 1:
                    # Multiple elements
                    extracted_data[field_name] = [
                        self._extract_element_data(elem) for elem in elements
                    ]
                else:
                    # No elements found
                    extracted_data[field_name] = None
                    
            except Exception as e:
                logger.warning(f"Failed to extract {field_name} with selector {selector}: {e}")
                extracted_data[field_name] = None
        
        # Apply variable substitution
        if context.variables:
            extracted_data = self._apply_variables(extracted_data, context.variables)
        
        return extracted_data
    
    def _extract_element_data(self, element) -> Dict[str, Any]:
        """Extract comprehensive data from a single element"""
        
        data = {
            'text': element.get_text(strip=True),
            'html': str(element)
        }
        
        # Extract attributes
        if element.attrs:
            data['attributes'] = dict(element.attrs)
        
        # Extract specific useful attributes
        if element.get('href'):
            data['url'] = element.get('href')
        if element.get('src'):
            data['image_url'] = element.get('src')
        if element.get('alt'):
            data['alt_text'] = element.get('alt')
        if element.get('title'):
            data['title'] = element.get('title')
        
        # Extract structured data (JSON-LD, microdata, etc.)
        if element.get('type') == 'application/ld+json':
            try:
                data['structured_data'] = json.loads(element.string)
            except:
                pass
        
        return data
    
    def _apply_variables(self, data: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """Apply variable substitution to extracted data"""
        
        def substitute_recursive(obj):
            if isinstance(obj, str):
                for var_name, var_value in variables.items():
                    obj = obj.replace(f"{{{var_name}}}", str(var_value))
                return obj
            elif isinstance(obj, dict):
                return {k: substitute_recursive(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute_recursive(item) for item in obj]
            else:
                return obj
        
        return substitute_recursive(data)

class BatchScrapingEngine:
    """
    Engine for batch scraping operations
    """
    
    def __init__(self, max_concurrent: int = None):
        self.max_concurrent = max_concurrent or settings.max_concurrent_requests
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.scraping_engine = ScrapingEngine()
    
    async def initialize(self):
        """Initialize the engine"""
        await self.scraping_engine.initialize()
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.scraping_engine.cleanup()
    
    async def scrape_batch(
        self, 
        contexts: List[ScrapingContext]
    ) -> List[ScrapingResult]:
        """Scrape multiple URLs concurrently"""
        
        async def scrape_with_semaphore(context: ScrapingContext) -> ScrapingResult:
            async with self.semaphore:
                return await self.scraping_engine.scrape(context)
        
        # Execute all scraping tasks concurrently
        tasks = [scrape_with_semaphore(context) for context in contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = ScrapingResult(success=False)
                error_result.errors.append(str(result))
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
