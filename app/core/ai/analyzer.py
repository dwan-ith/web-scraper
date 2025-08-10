"""
AI-Powered Website Structure Analysis
Intelligent site understanding and selector generation
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag
import json
import re
import openai
from anthropic import AsyncAnthropic

from app.config import settings
from app.utils.exceptions import AIAnalysisException

logger = logging.getLogger(__name__)

@dataclass
class PageStructure:
    """Represents the analyzed structure of a webpage"""
    title: str
    description: str
    main_content_selector: str
    navigation_selector: str
    article_selectors: List[str]
    list_selectors: List[str]
    data_tables: List[str]
    forms: List[str]
    semantic_regions: Dict[str, str]

@dataclass
class ContentAnalysis:
    """Analysis of page content and patterns"""
    content_type: str  # 'article', 'product', 'search_results', 'list', etc.
    patterns: Dict[str, str]
    selectors: Dict[str, str]
    confidence_score: float
    extraction_strategy: str

class SiteAnalyzer:
    """
    AI-powered website structure analyzer
    """
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        
        if settings.openai_api_key:
            openai.api_key = settings.openai_api_key
        
        if settings.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    async def analyze_page(self, html: str, user_query: str = "") -> Dict[str, Any]:
        """
        Comprehensive page analysis using AI
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract basic structure
            basic_structure = self._extract_basic_structure(soup)
            
            # Analyze content patterns
            content_analysis = await self._analyze_content_patterns(soup, user_query)
            
            # Generate smart selectors
            smart_selectors = await self._generate_smart_selectors(soup, user_query)
            
            # Detect data patterns
            data_patterns = self._detect_data_patterns(soup)
            
            # AI-powered semantic analysis
            semantic_analysis = await self._ai_semantic_analysis(html, user_query)
            
            return {
                'structure': basic_structure,
                'content_analysis': content_analysis,
                'selectors': smart_selectors,
                'data_patterns': data_patterns,
                'semantic_analysis': semantic_analysis,
                'confidence_score': content_analysis.confidence_score
            }
            
        except Exception as e:
            logger.error(f"Page analysis failed: {e}")
            raise AIAnalysisException(f"Analysis failed: {e}")
    
    def _extract_basic_structure(self, soup: BeautifulSoup) -> PageStructure:
        """Extract basic HTML structure elements"""
        
        # Get title
        title_elem = soup.find('title')
        title = title_elem.get_text(strip=True) if title_elem else ""
        
        # Get description
        desc_elem = soup.find('meta', attrs={'name': 'description'})
        description = desc_elem.get('content', '') if desc_elem else ""
        
        # Identify main content area
        main_content = self._find_main_content_selector(soup)
        
        # Identify navigation
        nav_selector = self._find_navigation_selector(soup)
        
        # Find article elements
        article_selectors = self._find_article_selectors(soup)
        
        # Find list structures
        list_selectors = self._find_list_selectors(soup)
        
        # Find data tables
        data_tables = self._find_data_table_selectors(soup)
        
        # Find forms
        forms = self._find_form_selectors(soup)
        
        # Semantic regions
        semantic_regions = self._find_semantic_regions(soup)
        
        return PageStructure(
            title=title,
            description=description,
            main_content_selector=main_content,
            navigation_selector=nav_selector,
            article_selectors=article_selectors,
            list_selectors=list_selectors,
            data_tables=data_tables,
            forms=forms,
            semantic_regions=semantic_regions
        )
    
    def _find_main_content_selector(self, soup: BeautifulSoup) -> str:
        """Identify the main content area"""
        
        # Priority order for main content
        main_selectors = [
            'main',
            '[role="main"]',
            '#main',
            '.main',
            '#content',
            '.content',
            '#main-content',
            '.main-content',
            'article',
            '.container .row .col-md-8',  # Common Bootstrap pattern
            '.content-area'
        ]
        
        for selector in main_selectors:
            if soup.select(selector):
                return selector
        
        # Fallback: find largest content area
        content_areas = soup.find_all(['div', 'section'], class_=re.compile(r'content|main|body'))
        if content_areas:
            largest = max(content_areas, key=lambda x: len(x.get_text()))
            return self._generate_selector_for_element(largest)
        
        return 'body'
    
    def _find_navigation_selector(self, soup: BeautifulSoup) -> str:
        """Find navigation elements"""
        
        nav_selectors = [
            'nav',
            '[role="navigation"]',
            '.navbar',
            '.nav',
            '.navigation',
            '#navigation',
            '.menu',
            '#menu'
        ]
        
        for selector in nav_selectors:
            if soup.select(selector):
                return selector
        
        return ""
    
    def _find_article_selectors(self, soup: BeautifulSoup) -> List[str]:
        """Find article-like content"""
        
        selectors = []
        
        # Semantic article tags
        if soup.select('article'):
            selectors.append('article')
        
        # Common article class patterns
        article_patterns = [
            '.article',
            '.post',
            '.entry',
            '.story',
            '.news-item',
            '.blog-post',
            '[itemtype*="Article"]'
        ]
        
        for pattern in article_patterns:
            if soup.select(pattern):
                selectors.append(pattern)
        
        return selectors
    
    def _find_list_selectors(self, soup: BeautifulSoup) -> List[str]:
        """Find list structures"""
        
        selectors = []
        
        # Standard lists
        if soup.select('ul li'):
            selectors.append('ul li')
        if soup.select('ol li'):
            selectors.append('ol li')
        
        # Common list patterns
        list_patterns = [
            '.list-item',
            '.item',
            '.result',
            '.product',
            '.card',
            '.tile',
            '[class*="item-"]',
            '[class*="list-"]'
        ]
        
        for pattern in list_patterns:
            elements = soup.select(pattern)
            if len(elements) > 2:  # Multiple items indicate a list
                selectors.append(pattern)
        
        return selectors
    
    def _find_data_table_selectors(self, soup: BeautifulSoup) -> List[str]:
        """Find data tables"""
        
        selectors = []
        
        tables = soup.select('table')
        for table in tables:
            if table.select('th') or table.select('thead'):  # Has headers
                selector = self._generate_selector_for_element(table)
                selectors.append(selector)
        
        # CSS Grid/Flexbox tables
        grid_tables = soup.select('[class*="table"], [class*="grid"], [class*="data"]')
        for table in grid_tables:
            if len(table.select('[class*="row"], [class*="item"]')) > 2:
                selector = self._generate_selector_for_element(table)
                selectors.append(selector)
        
        return selectors
    
    def _find_form_selectors(self, soup: BeautifulSoup) -> List[str]:
        """Find form elements"""
        
        selectors = []
        
        forms = soup.select('form')
        for form in forms:
            selector = self._generate_selector_for_element(form)
            selectors.append(selector)
        
        return selectors
    
    def _find_semantic_regions(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Find semantic HTML5 regions"""
        
        regions = {}
        
        semantic_tags = ['header', 'footer', 'aside', 'section', 'main', 'nav']
        
        for tag in semantic_tags:
            elements = soup.select(tag)
            if elements:
                regions[tag] = tag
        
        # ARIA landmarks
        landmarks = [
            ('banner', '[role="banner"]'),
            ('navigation', '[role="navigation"]'),
            ('main', '[role="main"]'),
            ('complementary', '[role="complementary"]'),
            ('contentinfo', '[role="contentinfo"]'),
            ('search', '[role="search"]')
        ]
        
        for name, selector in landmarks:
            if soup.select(selector):
                regions[name] = selector
        
        return regions
    
    async def _analyze_content_patterns(self, soup: BeautifulSoup, user_query: str) -> ContentAnalysis:
        """Analyze content patterns and determine page type"""
        
        # Analyze page structure
        has_articles = bool(soup.select('article, .post, .entry'))
        has_products = bool(soup.select('.product, [itemtype*="Product"]'))
        has_listings = len(soup.select('.item, .result, .listing')) > 3
        has_tables = bool(soup.select('table'))
        has_forms = bool(soup.select('form'))
        
        # Determine content type
        if has_products:
            content_type = "ecommerce"
        elif has_articles:
            content_type = "editorial"
        elif has_listings:
            content_type = "directory"
        elif has_tables:
            content_type = "data_table"
        elif has_forms:
            content_type = "form"
        else:
            content_type = "general"
        
        # Generate extraction strategy
        patterns = self._identify_content_patterns(soup, content_type)
        selectors = self._generate_selectors_for_patterns(soup, patterns, user_query)
        
        # Calculate confidence based on pattern strength
        confidence = self._calculate_confidence(patterns, selectors)
        
        # Determine extraction strategy
        if user_query:
            strategy = "ai_guided"
        elif content_type in ["ecommerce", "editorial"]:
            strategy = "structured"
        else:
            strategy = "heuristic"
        
        return ContentAnalysis(
            content_type=content_type,
            patterns=patterns,
            selectors=selectors,
            confidence_score=confidence,
            extraction_strategy=strategy
        )
    
    def _identify_content_patterns(self, soup: BeautifulSoup, content_type: str) -> Dict[str, str]:
        """Identify content patterns based on page type"""
        
        patterns = {}
        
        if content_type == "ecommerce":
            patterns.update({
                "product_title": "h1, .product-title, [itemprop='name']",
                "price": ".price, [itemprop='price'], .cost",
                "description": ".description, [itemprop='description']",
                "images": ".product-image img, .gallery img",
                "rating": ".rating, .stars, [itemprop='ratingValue']",
                "availability": "[itemprop='availability'], .availability"
            })
        
        elif content_type == "editorial":
            patterns.update({
                "title": "h1, .article-title, .post-title",
                "author": ".author, [rel='author'], [itemprop='author']",
                "date": ".date, [datetime], [itemprop='datePublished']",
                "content": ".content, .article-body, .post-content",
                "tags": ".tags a, .categories a",
                "summary": ".excerpt, .summary, .abstract"
            })
        
        elif content_type == "directory":
            patterns.update({
                "items": ".item, .result, .listing, .card",
                "title": ".title, .name, h2, h3",
                "link": "a[href]",
                "description": ".description, .excerpt",
                "metadata": ".meta, .info, .details"
            })
        
        return patterns
    
    def _generate_selectors_for_patterns(self, soup: BeautifulSoup, patterns: Dict[str, str], user_query: str) -> Dict[str, str]:
        """Generate optimized selectors for identified patterns"""
        
        optimized_selectors = {}
        
        for field, selector in patterns.items():
            # Test the selector
            elements = soup.select(selector)
            
            if elements:
                # Optimize selector specificity
                optimized_selector = self._optimize_selector(soup, selector, elements)
                optimized_selectors[field] = optimized_selector
            else:
                # Try to find alternative selector
                alternative = self._find_alternative_selector(soup, field, user_query)
                if alternative:
                    optimized_selectors[field] = alternative
        
        return optimized_selectors
    
    def _optimize_selector(self, soup: BeautifulSoup, selector: str, elements: List[Tag]) -> str:
        """Optimize selector for better specificity and performance"""
        
        if len(elements) == 1:
            # Perfect match, return as is
            return selector
        
        # Try to make selector more specific
        first_element = elements[0]
        
        # Add parent context if needed
        parent = first_element.parent
        if parent and parent.name != 'body':
            parent_selector = self._generate_selector_for_element(parent)
            combined = f"{parent_selector} {selector}"
            if len(soup.select(combined)) < len(elements):
                return combined
        
        # Add :first-of-type or :nth-child if multiple elements
        if len(elements) > 1:
            return f"{selector}:first-of-type"
        
        return selector
    
    def _find_alternative_selector(self, soup: BeautifulSoup, field: str, user_query: str) -> Optional[str]:
        """Find alternative selector when primary selector fails"""
        
        # Common alternative patterns by field type
        alternatives = {
            "title": ["h1", "h2", ".title", ".heading", "[class*='title']"],
            "price": ["[class*='price']", "[class*='cost']", "[data-price]"],
            "description": ["p", ".desc", "[class*='desc']", ".summary"],
            "author": ["[class*='author']", "[class*='by']", ".byline"],
            "date": ["time", "[class*='date']", "[class*='time']", ".published"],
            "link": ["a[href]", "[data-url]", "[data-link]"]
        }
        
        if field in alternatives:
            for alt_selector in alternatives[field]:
                if soup.select(alt_selector):
                    return alt_selector
        
        return None
    
    def _calculate_confidence(self, patterns: Dict[str, str], selectors: Dict[str, str]) -> float:
        """Calculate confidence score for the analysis"""
        
        if not patterns:
            return 0.0
        
        # Base confidence on pattern coverage
        coverage = len(selectors) / len(patterns)
        
        # Bonus for semantic selectors
        semantic_bonus = 0
        for selector in selectors.values():
            if any(sem in selector for sem in ['[itemprop', '[itemtype', 'article', 'header']):
                semantic_bonus += 0.1
        
        confidence = min(1.0, coverage + semantic_bonus)
        
        return round(confidence, 2)
    
    async def _generate_smart_selectors(self, soup: BeautifulSoup, user_query: str) -> Dict[str, str]:
        """Generate intelligent selectors based on user query"""
        
        if not user_query:
            return {}
        
        # Use AI to understand what user wants
        if self.openai_client or self.anthropic_client:
            return await self._ai_generate_selectors(soup, user_query)
        else:
            # Fallback to heuristic approach
            return self._heuristic_selector_generation(soup, user_query)
    
    async def _ai_generate_selectors(self, soup: BeautifulSoup, user_query: str) -> Dict[str, str]:
        """Use AI to generate selectors based on user query"""
        
        # Prepare simplified HTML structure for AI
        simplified_html = self._simplify_html_for_ai(soup)
        
        prompt = f"""
        Analyze this HTML structure and generate CSS selectors to extract the data requested by the user.

        User Query: "{user_query}"

        HTML Structure (simplified):
        {simplified_html}

        Generate CSS selectors as a JSON object where keys are field names and values are CSS selectors.
        Focus on robust selectors that will work reliably.

        Example response:
        {{
            "titles": ".product-title",
            "prices": ".price-amount",
            "descriptions": ".product-description"
        }}
        """
        
        try:
            if self.anthropic_client:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            else:
                # OpenAI fallback
                response = await openai.ChatCompletion.acreate(
                    model=settings.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000
                )
                content = response.choices[0].message.content
            
            # Parse JSON response
            selectors = json.loads(content)
            
            # Validate selectors
            validated_selectors = {}
            for field, selector in selectors.items():
                if soup.select(selector):
                    validated_selectors[field] = selector
            
            return validated_selectors
            
        except Exception as e:
            logger.warning(f"AI selector generation failed: {e}")
            return self._heuristic_selector_generation(soup, user_query)
    
    def _simplify_html_for_ai(self, soup: BeautifulSoup) -> str:
        """Simplify HTML structure for AI analysis"""
        
        # Create a simplified version showing structure
        simplified_elements = []
        
        # Get important elements with their structure
        for elem in soup.find_all(['div', 'section', 'article', 'ul', 'table', 'h1', 'h2', 'h3']):
            elem_info = {
                'tag': elem.name,
                'classes': elem.get('class', []),
                'id': elem.get('id', ''),
                'text_preview': elem.get_text(strip=True)[:100]
            }
            simplified_elements.append(elem_info)
        
        # Limit to first 50 elements to stay within token limits
        return json.dumps(simplified_elements[:50], indent=2)
    
    def _heuristic_selector_generation(self, soup: BeautifulSoup, user_query: str) -> Dict[str, str]:
        """Generate selectors using heuristic approach"""
        
        selectors = {}
        query_lower = user_query.lower()
        
        # Common data extraction patterns
        if any(word in query_lower for word in ['title', 'heading', 'name']):
            if soup.select('h1'):
                selectors['title'] = 'h1'
            elif soup.select('.title'):
                selectors['title'] = '.title'
        
        if any(word in query_lower for word in ['price', 'cost', 'amount']):
            for price_sel in ['.price', '[class*="price"]', '[data-price]']:
                if soup.select(price_sel):
                    selectors['price'] = price_sel
                    break
        
        if any(word in query_lower for word in ['description', 'content', 'text']):
            for desc_sel in ['.description', '.content', 'p']:
                if soup.select(desc_sel):
                    selectors['description'] = desc_sel
                    break
        
        if any(word in query_lower for word in ['link', 'url', 'href']):
            selectors['links'] = 'a[href]'
        
        if any(word in query_lower for word in ['image', 'photo', 'picture']):
            selectors['images'] = 'img[src]'
        
        return selectors
    
    def _detect_data_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Detect structured data patterns"""
        
        patterns = {
            'json_ld': [],
            'microdata': [],
            'open_graph': [],
            'twitter_cards': [],
            'structured_tables': []
        }
        
        # JSON-LD structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                patterns['json_ld'].append(data)
            except:
                pass
        
        # Microdata
        microdata_elements = soup.find_all(attrs={'itemscope': True})
        for elem in microdata_elements:
            itemtype = elem.get('itemtype', '')
            patterns['microdata'].append({
                'type': itemtype,
                'selector': self._generate_selector_for_element(elem)
            })
        
        # Open Graph
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        patterns['open_graph'] = {tag.get('property'): tag.get('content') for tag in og_tags}
        
        # Twitter Cards
        twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
        patterns['twitter_cards'] = {tag.get('name'): tag.get('content') for tag in twitter_tags}
        
        # Structured tables
        for table in soup.find_all('table'):
            if table.find('th') or table.find('thead'):
                patterns['structured_tables'].append({
                    'selector': self._generate_selector_for_element(table),
                    'headers': [th.get_text(strip=True) for th in table.find_all('th')]
                })
        
        return patterns
    
    async def _ai_semantic_analysis(self, html: str, user_query: str) -> Dict[str, Any]:
        """Perform semantic analysis of page content using AI"""
        
        if not (self.openai_client or self.anthropic_client):
            return {}
        
        # Extract text content for analysis
        soup = BeautifulSoup(html, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)[:5000]  # Limit for token usage
        
        prompt = f"""
        Analyze this webpage content and provide semantic insights:

        User Query: "{user_query}"
        
        Page Content: "{text_content}"
        
        Provide analysis as JSON with:
        1. page_type: (product, article, directory, etc.)
        2. main_entities: List of key entities/topics
        3. data_relationships: How different data pieces relate
        4. extraction_recommendations: Best strategies for this content type
        """
        
        try:
            if self.anthropic_client:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
            else:
                response = await openai.ChatCompletion.acreate(
                    model=settings.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000
                )
                content = response.choices[0].message.content
            
            return json.loads(content)
            
        except Exception as e:
            logger.warning(f"AI semantic analysis failed: {e}")
            return {}
    
    def _generate_selector_for_element(self, element: Tag) -> str:
        """Generate a CSS selector for a specific element"""
        
        selectors = []
        
        # Use ID if available
        if element.get('id'):
            return f"#{element['id']}"
        
        # Use unique class combinations
        if element.get('class'):
            classes = element['class']
            class_selector = '.' + '.'.join(classes)
            selectors.append(class_selector)
        
        # Use tag name as fallback
        selectors.append(element.name)
        
        return selectors[0] if selectors else element.name