"""
Scraper Service — Orchestrates: HAR → LLM → Storage → Execute
"""
import json
import logging
import uuid
from typing import Any, Optional

from app.core.scraper.har_analyzer import HarAnalyzer
from app.core.ai.reverse_engineer import AIReverseEngineer, GeneratedEndpoint
from app.core.scraper.engine import ExecutionEngine
from app.core.storage.cache import get_cache

logger = logging.getLogger(__name__)


class ScraperService:
    def __init__(self):
        self.har_analyzer = HarAnalyzer()
        self.ai = AIReverseEngineer()
        self.executor = ExecutionEngine()
        self.cache = None
        self._initialized = False

    async def initialize(self):
        if not self._initialized:
            self.cache = await get_cache()
            self._initialized = True

    # ── HAR → LLM → Persist ─────────────────────────────────────────────────

    async def generate_from_har(
        self, user_id: str, har_data: dict, goal: str, name: str
    ) -> dict[str, Any]:
        """
        Core pipeline:
        1. Distill .HAR → minimal API-only entries
        2. LLM identifies the target endpoint (GeneratedEndpoint)
        3. Render as executable Python code
        4. Persist to cache
        """
        await self.initialize()

        distilled_har = self.har_analyzer.process_har(har_data)
        token_estimate = self.har_analyzer.estimate_tokens(distilled_har)
        logger.info(f"Estimated token usage: ~{token_estimate:,}")

        endpoint: GeneratedEndpoint = await self.ai.identify_api(distilled_har, goal)
        generated_code = endpoint.to_python_function()

        scraper_id = str(uuid.uuid4())
        record = {
            "id": scraper_id,
            "user_id": user_id,
            "name": name,
            "goal": goal,
            "status": "active",
            "confidence": endpoint.confidence,
            "endpoint": endpoint.model_dump(),
            "generated_code": generated_code,
        }

        await self.cache.set(
            f"scraper:{scraper_id}",
            json.dumps(record),
            ttl=86400 * 30,  # 30 days
        )

        return {
            "id": scraper_id,
            "name": name,
            "goal": goal,
            "status": "active",
            "confidence": endpoint.confidence,
            "target_url": endpoint.target_url,
            "method": endpoint.http_method,
            "reasoning": endpoint.reasoning,
            "generated_code": generated_code,
        }

    # ── Retrieve ─────────────────────────────────────────────────────────────

    async def get_scraper(self, scraper_id: str, user_id: str) -> dict[str, Any]:
        await self.initialize()
        raw = await self.cache.get(f"scraper:{scraper_id}")
        if not raw:
            raise KeyError(f"Scraper '{scraper_id}' not found")
        record = json.loads(raw)
        if record.get("user_id") != user_id:
            raise PermissionError("Access denied")
        return record

    async def list_scrapers(self, user_id: str) -> dict[str, Any]:
        # Full listing requires DB scan; for now Redis-backed per-user key
        await self.initialize()
        raw = await self.cache.get(f"scrapers:user:{user_id}")
        ids: list = json.loads(raw) if raw else []
        return {"user_id": user_id, "count": len(ids), "ids": ids}

    # ── Execute ───────────────────────────────────────────────────────────────

    async def execute_scraper(
        self,
        scraper_id: str,
        user_id: str,
        variables: Optional[dict[str, str]] = None,
        page: Optional[int] = None,
        use_code_execution: bool = False,
    ) -> dict[str, Any]:
        """
        Executes a saved scraper.
        use_code_execution=True → runs the LLM-generated Python function (Parse.bot mode)
        use_code_execution=False → direct httpx replay (default, more controlled)
        """
        record = await self.get_scraper(scraper_id, user_id)
        endpoint = GeneratedEndpoint(**record["endpoint"])

        if use_code_execution:
            return await self.executor.execute_generated_code(endpoint, variables, page)
        return await self.executor.execute(endpoint, variables, page)