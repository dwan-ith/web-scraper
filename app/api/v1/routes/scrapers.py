"""
HAR-based API Generator Routes
POST /api/v1/scrapers/generate  - Upload HAR + goal, get a reverse-engineered API
POST /api/v1/scrapers/{id}/run  - Execute the generated API endpoint
GET  /api/v1/scrapers/{id}      - Retrieve saved scraper schema
GET  /api/v1/scrapers/          - List all scrapers
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict
import json, logging

from app.services.scraper_service import ScraperService
from app.services.auth_service import get_current_user

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

scraper_service = ScraperService()

class RunRequest(BaseModel):
    variables: Optional[Dict[str, str]] = None

# ─── Generate a new API from a HAR file ────────────────────────────────────
@router.post("/generate", summary="Upload a .HAR file and a goal to auto-generate a scraper API")
async def generate_from_har(
    har_file: UploadFile = File(..., description="Chrome DevTools .HAR export"),
    goal: str = Form(..., description="Natural language goal e.g. 'find all paper DOIs'"),
    name: str = Form(..., description="Human readable name for this scraper"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user = Depends(get_current_user)
):
    """
    The core endpoint. Accepts a .HAR network log and a plain-English goal.
    1. Distills the HAR to isolate XHR/fetch traffic
    2. Sends it to the LLM to identify the exact hidden API
    3. Saves the reverse-engineered request schema
    """
    try:
        contents = await har_file.read()
        har_data = json.loads(contents)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid .HAR file. Must be valid JSON.")

    try:
        result = await scraper_service.generate_from_har(
            user_id=current_user.id,
            har_data=har_data,
            goal=goal,
            name=name
        )
        return result
    except Exception as e:
        logger.error(f"HAR generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Execute a saved scraper ─────────────────────────────────────────────────
@router.post("/{scraper_id}/run", summary="Execute a saved reverse-engineered API")
async def run_scraper(
    scraper_id: str,
    body: RunRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user = Depends(get_current_user)
):
    """
    Executes the stored reverse-engineered API endpoint directly via httpx.
    Optional variables are applied to the URL/payload before the request.
    """
    try:
        result = await scraper_service.execute_scraper(
            scraper_id=scraper_id,
            user_id=current_user.id,
            variables=body.variables
        )
        return result
    except Exception as e:
        logger.error(f"Scraper run failed for {scraper_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Get a saved scraper ──────────────────────────────────────────────────────
@router.get("/{scraper_id}", summary="Retrieve a saved scraper schema")
async def get_scraper(
    scraper_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user = Depends(get_current_user)
):
    try:
        return await scraper_service.get_scraper(scraper_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── List all scrapers ────────────────────────────────────────────────────────
@router.get("/", summary="List all saved scrapers for this user")
async def list_scrapers(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user = Depends(get_current_user)
):
    try:
        return await scraper_service.list_scrapers(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))