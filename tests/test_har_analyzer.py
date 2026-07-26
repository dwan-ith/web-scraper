"""
Tests for HarAnalyzer — covering filtering, token estimation, and sorting.
"""
import json
import pytest
from app.core.scraper.har_analyzer import HarAnalyzer


def _make_entry(method="GET", url="https://api.example.com/data", mime="application/json", size=500, status=200, body="", res_text='{"data": [1,2,3]}'):
    return {
        "request": {
            "method": method,
            "url": url,
            "headers": [
                {"name": "Authorization", "value": "Bearer tok123"},
                {"name": "Accept", "value": "application/json"},
                {"name": "user-agent", "value": "Mozilla/5.0"},
                {"name": "sec-ch-ua", "value": '"Chromium"'},
            ],
            "postData": {"text": body} if body else {},
        },
        "response": {
            "status": status,
            "content": {
                "mimeType": mime,
                "size": size,
                "text": res_text,
            },
        },
    }


class TestHarAnalyzer:
    def setup_method(self):
        self.analyzer = HarAnalyzer()

    def _wrap(self, entries):
        return {"log": {"entries": entries}}

    def test_filters_out_images(self):
        entries = [
            _make_entry(mime="image/png", url="https://cdn.example.com/logo.png"),
            _make_entry(mime="application/json", url="https://api.example.com/data"),
        ]
        result = self.analyzer.process_har(self._wrap(entries))
        assert len(result) == 1
        assert "api.example.com" in result[0]["url"]

    def test_filters_out_css_and_js(self):
        entries = [
            _make_entry(mime="text/css", url="https://example.com/style.css"),
            _make_entry(mime="application/javascript", url="https://example.com/app.js"),
            _make_entry(mime="application/json", url="https://api.example.com/users"),
        ]
        result = self.analyzer.process_har(self._wrap(entries))
        assert len(result) == 1

    def test_filters_out_options_requests(self):
        entries = [
            _make_entry(method="OPTIONS", url="https://api.example.com/preflight"),
            _make_entry(method="POST", url="https://api.example.com/submit"),
        ]
        result = self.analyzer.process_har(self._wrap(entries))
        assert len(result) == 1
        assert result[0]["method"] == "POST"

    def test_strips_noise_headers_keeps_auth(self):
        entries = [_make_entry()]
        result = self.analyzer.process_har(self._wrap(entries))
        headers = result[0]["req_headers"]
        # Authorization should be kept
        assert "authorization" in headers
        # Browser noise headers should be dropped
        assert "user-agent" not in headers
        assert "sec-ch-ua" not in headers

    def test_sorts_by_response_size_descending(self):
        entries = [
            _make_entry(size=100, url="https://api.example.com/small"),
            _make_entry(size=9000, url="https://api.example.com/large"),
            _make_entry(size=500, url="https://api.example.com/medium"),
        ]
        result = self.analyzer.process_har(self._wrap(entries))
        sizes = [e["res_size"] for e in result]
        assert sizes == sorted(sizes, reverse=True)

    def test_filters_analytics_domains(self):
        entries = [
            _make_entry(url="https://www.google-analytics.com/collect"),
            _make_entry(url="https://doubleclick.net/pixel"),
            _make_entry(url="https://api.myapp.com/data"),
        ]
        result = self.analyzer.process_har(self._wrap(entries))
        assert len(result) == 1
        assert "myapp.com" in result[0]["url"]

    def test_empty_har(self):
        result = self.analyzer.process_har({"log": {"entries": []}})
        assert result == []

    def test_malformed_har_returns_empty(self):
        result = self.analyzer.process_har({})
        assert result == []

    def test_token_estimate_is_numeric(self):
        entries = [_make_entry(), _make_entry(url="https://api.example.com/other")]
        distilled = self.analyzer.process_har(self._wrap(entries))
        tokens = self.analyzer.estimate_tokens(distilled)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_response_preview_truncated(self):
        long_json = json.dumps({"items": list(range(10000))})
        entries = [_make_entry(res_text=long_json, size=len(long_json))]
        result = self.analyzer.process_har(self._wrap(entries))
        assert len(result[0]["res_preview"]) <= 620  # max_response_preview + small overhead
