"""
Scraper Management API Routes
Create, manage, and execute web scrapers
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from uuid import uuid4
import logging

from app.api.v1.models.scraper import (
    ScraperCreate, ScraperResponse, ScraperUpdate,
    ScraperRun, ScraperRunResponse, ScrapersList
)
from app.services.scraper_service import ScraperService
from app.services.auth_service import get_current_user
from app.core.scraper.engine import ScrapingContext, ScrapingEngine
from app.utils.exceptions import ScraperNotFoundException

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Initialize services
scraper_service = ScraperService()
scraping_engine = ScrapingEngine()

@router.post("/", response_model=ScraperResponse)
async def create_scraper(
    scraper_data: ScraperCreate,
    current_user = Depends(get_current_user)
):
    """
    Create a new scraper configuration
    """
    try:
        # Generate unique scraper ID
        scraper_id = str(uuid4())
        
        # Create scraper with AI analysis
        scraper = await scraper_service.create_scraper(
            scraper_id=scraper_id,
            user_id=current_user.id,
            data=scraper_data
        )
        
        logger.info(f"Created scraper {scraper_id} for user {current_user.id}")
        return scraper
        
    except Exception as e:
        logger.error(f"Failed to create scraper: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=ScrapersList)
async def list_scrapers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    search: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """
    List user's scrapers with pagination and search
    """
    try:
        scrapers = await scraper_service.list_scrapers(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            search=search
        )
        
        return scrapers
        
    except Exception as e:
        logger.error(f"Failed to list scrapers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{scraper_id}", response_model=ScraperResponse)
async def get_scraper(
    scraper_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get specific scraper details
    """
    try:
        scraper = await scraper_service.get_scraper(scraper_id, current_user.id)
        
        if not scraper:
            raise HTTPException(status_code=404, detail="Scraper not found")
        
        return scraper
        
    except ScraperNotFoundException:
        raise HTTPException(status_code=404, detail="Scraper not found")
    except Exception as e:
        logger.error(f"Failed to get scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{scraper_id}", response_model=ScraperResponse)
async def update_scraper(
    scraper_id: str,
    scraper_data: ScraperUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update scraper configuration
    """
    try:
        scraper = await scraper_service.update_scraper(
            scraper_id=scraper_id,
            user_id=current_user.id,
            data=scraper_data
        )
        
        if not scraper:
            raise HTTPException(status_code=404, detail="Scraper not found")
        
        logger.info(f"Updated scraper {scraper_id} for user {current_user.id}")
        return scraper
        
    except ScraperNotFoundException:
        raise HTTPException(status_code=404, detail="Scraper not found")
    except Exception as e:
        logger.error(f"Failed to update scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{scraper_id}")
async def delete_scraper(
    scraper_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete a scraper
    """
    try:
        success = await scraper_service.delete_scraper(scraper_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Scraper not found")
        
        logger.info(f"Deleted scraper {scraper_id} for user {current_user.id}")
        return {"message": "Scraper deleted successfully"}
        
    except ScraperNotFoundException:
        raise HTTPException(status_code=404, detail="Scraper not found")
    except Exception as e:
        logger.error(f"Failed to delete scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{scraper_id}/run", response_model=ScraperRunResponse)
async def run_scraper(
    scraper_id: str,
    run_data: ScraperRun,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Execute a scraper (sync or async)
    """
    try:
        # Get scraper configuration
        scraper = await scraper_service.get_scraper(scraper_id, current_user.id)
        if not scraper:
            raise HTTPException(status_code=404, detail="Scraper not found")
        
        # Create scraping context
        context = ScrapingContext(
            url=scraper.url,
            user_query=scraper.query,
            selectors=scraper.selectors,
            variables=run_data.variables or {},
            options=scraper.options or {},
            ai_enabled=scraper.ai_enabled
        )
        
        # Apply runtime variables
        if run_data.variables:
            context.url = context.url.format(**run_data.variables)
        
        # Execute scraping
        if run_data.async_execution:
            # Run in background
            run_id = str(uuid4())
            background_tasks.add_task(
                scraper_service.run_scraper_async,
                scraper_id, run_id, context, current_user.id
            )
            
            return ScraperRunResponse(
                run_id=run_id,
                status="running",
                message="Scraper started in background"
            )
        else:
            # Run synchronously
            result = await scraping_engine.scrape(context)
            
            # Save run result
            run_id = str(uuid4())
            await scraper_service.save_run_result(
                scraper_id, run_id, result, current_user.id
            )
            
            return ScraperRunResponse(
                run_id=run_id,
                status="completed" if result.success else "failed",
                data=result.data,
                metadata=result.metadata,
                errors=result.errors,
                execution_time=result.execution_time
            )
        
    except ScraperNotFoundException:
        raise HTTPException(status_code=404, detail="Scraper not found")
    except Exception as e:
        logger.error(f"Failed to run scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{scraper_id}/runs")
async def get_scraper_runs(
    scraper_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    current_user = Depends(get_current_user)
):
    """
    Get scraper execution history
    """
    try:
        runs = await scraper_service.get_scraper_runs(
            scraper_id=scraper_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        
        return runs
        
    except ScraperNotFoundException:
        raise HTTPException(status_code=404, detail="Scraper not found")
    except Exception as e:
        logger.error(f"Failed to get runs for scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{scraper_id}/runs/{run_id}")
async def get_run_details(
    scraper_id: str,
    run_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get specific run details
    """
    try:
        run = await scraper_service.get_run_details(
            scraper_id=scraper_id,
            run_id=run_id,
            user_id=current_user.id
        )
        
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return run
        
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{scraper_id}/test")
async def test_scraper(
    scraper_id: str,
    test_data: Optional[Dict[str, Any]] = None,
    current_user = Depends(get_current_user)
):
    """
    Test a scraper configuration without saving results
    """
    try:
        # Get scraper configuration
        scraper = await scraper_service.get_scraper(scraper_id, current_user.id)
        if not scraper:
            raise HTTPException(status_code=404, detail="Scraper not found")
        
        # Create test context
        context = ScrapingContext(
            url=scraper.url,
            user_query=scraper.query,
            selectors=scraper.selectors,
            variables=test_data or {},
            options=scraper.options or {},
            ai_enabled=scraper.ai_enabled,
            timeout=10  # Shorter timeout for testing
        )
        
        # Run test scraping
        result = await scraping_engine.scrape(context)
        
        return {
            "success": result.success,
            "sample_data": result.data,
            "selectors_used": result.selectors_used,
            "execution_time": result.execution_time,
            "errors": result.errors[:3],  # Limit errors for testing
            "metadata": {
                "strategy": result.metadata.get('strategy'),
                "retries": result.metadata.get('retries', 0)
            }
        }
        
    except ScraperNotFoundException:
        raise HTTPException(status_code=404, detail="Scraper not found")
    except Exception as e:
        logger.error(f"Failed to test scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{scraper_id}/schedule")
async def schedule_scraper(
    scraper_id: str,
    schedule_data: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Schedule periodic scraper execution
    """
    try:
        # Validate scraper exists
        scraper = await scraper_service.get_scraper(scraper_id, current_user.id)
        if not scraper:
            raise HTTPException(status_code=404, detail="Scraper not found")
        
        # Create schedule
        schedule = await scraper_service.create_schedule(
            scraper_id=scraper_id,
            user_id=current_user.id,
            schedule_config=schedule_data
        )
        
        logger.info(f"Scheduled scraper {scraper_id} for user {current_user.id}")
        return schedule
        
    except ScraperNotFoundException:
        raise HTTPException(status_code=404, detail="Scraper not found")
    except Exception as e:
        logger.error(f"Failed to schedule scraper {scraper_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{scraper_id}/analytics")
async def get_scraper_analytics(
    scraper_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_user)
):
    """
    Get scraper performance analytics
    """
    try: