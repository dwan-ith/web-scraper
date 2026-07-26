"""
Execution Engine — Parse.bot level
Executes reverse-engineered API endpoints directly via httpx.
Also supports dynamic code execution of the LLM-generated Python function.
"""
import httpx
import json
import logging
from typing import Any, Optional
from app.core.ai.reverse_engineer import GeneratedEndpoint

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Executes a GeneratedEndpoint in one of two modes:

    1. Direct mode (default, production-ready):
       Replays the httpx call defined by the GeneratedEndpoint fields.

    2. Code mode:
       Executes the LLM-generated Python async function in a sandboxed
       exec() scope — exactly what Parse.bot does.
    """

    async def execute(
        self,
        endpoint: GeneratedEndpoint,
        variables: Optional[dict[str, str]] = None,
        page: Optional[int] = None,
    ) -> dict[str, Any]:
        """Primary execution path — direct httpx replay."""
        url = endpoint.target_url
        payload = json.loads(json.dumps(endpoint.payload_template)) if endpoint.payload_template else None
        params: dict = {}

        # Variable substitution in URL and payload
        if variables:
            for k, v in variables.items():
                url = url.replace(f"{{{k}}}", str(v))
            if payload:
                payload_str = json.dumps(payload)
                for k, v in variables.items():
                    payload_str = payload_str.replace(f"{{{k}}}", str(v))
                payload = json.loads(payload_str)

        # Pagination
        if page is not None and endpoint.pagination_param:
            params[endpoint.pagination_param] = page

        logger.info(f"[Engine] {endpoint.http_method} {url}")

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            try:
                response = await client.request(
                    method=endpoint.http_method,
                    url=url,
                    headers=endpoint.required_headers,
                    params=params if params else None,
                    json=payload,
                )
                response.raise_for_status()
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_text": response.text}

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "execution_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                    "url_called": str(response.url),
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"[Engine] HTTP error {e.response.status_code}: {e}")
                return {"success": False, "error": f"HTTP {e.response.status_code}", "detail": str(e)}
            except Exception as e:
                logger.error(f"[Engine] Execution failed: {e}")
                return {"success": False, "error": str(e)}

    async def execute_generated_code(
        self,
        endpoint: GeneratedEndpoint,
        variables: Optional[dict[str, str]] = None,
        page: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Executes the LLM-generated Python function via exec().
        This is the Parse.bot-equivalent code generation path.
        The generated function is self-contained with its own httpx session.
        """
        import asyncio

        python_code = endpoint.to_python_function()
        logger.info("[Engine] Executing LLM-generated Python function...")

        exec_globals: dict = {}
        try:
            exec(compile(python_code, "<generated>", "exec"), exec_globals)
            fetch_fn = exec_globals.get("fetch")
            if not callable(fetch_fn):
                raise ValueError("Generated code did not produce a callable 'fetch' function")

            result = await fetch_fn(variables=variables or {}, page=page)
            return {"success": True, "data": result, "mode": "code_execution"}
        except Exception as e:
            logger.error(f"[Engine] Code execution failed: {e}\n\nGenerated code:\n{python_code}")
            return {"success": False, "error": str(e), "generated_code": python_code}
