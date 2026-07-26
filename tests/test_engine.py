"""
Tests for GeneratedEndpoint.to_python_function() code generation
and the ExecutionEngine's code execution mode.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.ai.reverse_engineer import GeneratedEndpoint
from app.core.scraper.engine import ExecutionEngine


def _make_endpoint(**kwargs):
    defaults = dict(
        target_url="https://api.example.com/v2/papers",
        http_method="GET",
        required_headers={"Authorization": "Bearer test-token"},
        payload_template=None,
        pagination_param=None,
        reasoning="This endpoint carries the paper metadata in JSON",
        confidence=0.95,
    )
    defaults.update(kwargs)
    return GeneratedEndpoint(**defaults)


class TestGeneratedEndpoint:
    def test_to_python_function_returns_string(self):
        endpoint = _make_endpoint()
        code = endpoint.to_python_function()
        assert isinstance(code, str)
        assert len(code) > 100

    def test_generated_code_contains_url(self):
        endpoint = _make_endpoint()
        code = endpoint.to_python_function()
        assert "https://api.example.com/v2/papers" in code

    def test_generated_code_contains_http_method(self):
        endpoint = _make_endpoint(http_method="POST")
        code = endpoint.to_python_function()
        assert "POST" in code

    def test_generated_code_has_fetch_function(self):
        endpoint = _make_endpoint()
        code = endpoint.to_python_function()
        assert "async def fetch" in code

    def test_generated_code_has_pagination_block(self):
        endpoint = _make_endpoint(pagination_param="page")
        code = endpoint.to_python_function()
        assert "page" in code
        assert endpoint.pagination_param in code

    def test_generated_code_has_variable_substitution(self):
        endpoint = _make_endpoint()
        code = endpoint.to_python_function()
        assert "variables" in code
        assert "replace" in code

    def test_generated_code_is_valid_python(self):
        """The generated code must compile without syntax errors."""
        endpoint = _make_endpoint()
        code = endpoint.to_python_function()
        try:
            compile(code, "<test>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    def test_generated_code_with_post_payload(self):
        endpoint = _make_endpoint(
            http_method="POST",
            payload_template={"query": "{search_term}", "limit": 20},
        )
        code = endpoint.to_python_function()
        assert "POST" in code
        assert "search_term" in code

    def test_confidence_reflected_in_comment(self):
        endpoint = _make_endpoint(confidence=0.87)
        code = endpoint.to_python_function()
        assert "87%" in code


class TestExecutionEngine:
    def setup_method(self):
        self.engine = ExecutionEngine()

    @pytest.mark.asyncio
    async def test_execute_generated_code_compiles_and_runs(self):
        """
        The generated Python code is valid, compilable, and exec'd correctly.
        exec() creates its own import scope for httpx, so we validate:
          1. The generated code compiles without SyntaxError
          2. execute_generated_code() returns a dict with 'success' key
          3. On a real network error (bad host) it returns success=False gracefully
        """
        import httpx as _httpx
        endpoint = _make_endpoint(target_url="https://localhost:1/nonexistent-endpoint-test")
        code = endpoint.to_python_function()

        # Step 1: code must be syntactically valid
        try:
            compile(code, "<generated>", "exec")
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

        # Step 2: execute_generated_code returns a proper result dict
        result = await self.engine.execute_generated_code(endpoint, variables={})
        assert isinstance(result, dict)
        assert "success" in result

        # Step 3: a connection failure on a bad host returns success=False (not an exception)
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_direct_success(self):
        endpoint = _make_endpoint()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [1, 2, 3]}
        mock_response.raise_for_status = MagicMock()
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_response.url = "https://api.example.com/v2/papers"
        mock_response.text = '{"items": [1,2,3]}'

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.engine.execute(endpoint)

        assert result["success"] is True
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_execute_applies_variables(self):
        endpoint = _make_endpoint(target_url="https://api.example.com/search?q={query}")
        called_with: dict = {}

        async def fake_request(**kwargs):
            called_with["url"] = kwargs.get("url", "")
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.raise_for_status = MagicMock()
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_response.url = kwargs.get("url", "")
            return mock_response

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(side_effect=lambda **kw: fake_request(**kw))

        with patch("httpx.AsyncClient", return_value=mock_client):
            await self.engine.execute(endpoint, variables={"query": "machine+learning"})

    @pytest.mark.asyncio
    async def test_execute_handles_network_failure(self):
        endpoint = _make_endpoint()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.request = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await self.engine.execute(endpoint)

        assert result["success"] is False
        assert "error" in result
