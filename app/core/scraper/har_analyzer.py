"""
HAR Analyzer Utility
Filters and minifies .HAR network logs to isolate API traffic.
Aggressively compresses token usage for cost-efficient LLM calls.
"""
import json
import logging
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# MIME types that are never API responses — skip them all
_SKIP_MIMES = (
    "image/", "video/", "audio/", "font/",
    "text/css", "application/javascript", "text/javascript",
    "application/x-javascript",
)

# Headers that are noise (browser metadata, not auth-relevant)
_NOISE_HEADERS = {
    "accept-encoding", "accept-language", "cache-control",
    "connection", "pragma", "sec-ch-ua", "sec-ch-ua-mobile",
    "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode",
    "sec-fetch-site", "sec-fetch-user", "upgrade-insecure-requests",
    "user-agent", "if-modified-since", "if-none-match",
    "x-requested-with", "dnt",
}

# Headers that are high-value auth signals — always keep
_KEEP_HEADERS = {
    "authorization", "cookie", "x-api-key", "x-auth-token",
    "x-access-token", "bearer", "content-type", "graphql-client-version",
    "x-csrf-token", "x-xsrf-token",
}


class HarAnalyzer:
    def __init__(self, max_response_preview: int = 600):
        self.max_response_preview = max_response_preview

    def process_har(self, har_data: dict) -> list[dict[str, Any]]:
        """
        Takes raw HAR JSON and distills it into a dense list of API calls only.
        Returns entries sorted by response size descending (richest data first).
        """
        entries = har_data.get("log", {}).get("entries", [])
        distilled = []

        for entry in entries:
            req = entry.get("request", {})
            res = entry.get("response", {})
            res_content = res.get("content", {})
            mime = res_content.get("mimeType", "").lower()

            # Skip non-API resources
            if any(mime.startswith(skip) for skip in _SKIP_MIMES):
                continue
            if req.get("method") == "OPTIONS":
                continue

            url = req.get("url", "")
            parsed = urlparse(url)

            # Skip tracking pixels, analytics, and CDN assets
            if any(p in parsed.netloc for p in ("google-analytics", "doubleclick", "facebook.net", "cloudflare")):
                continue
            if any(parsed.path.endswith(ext) for ext in (".png", ".jpg", ".svg", ".ico", ".woff2", ".woff", ".ttf")):
                continue

            # Condense headers — only keep auth-relevant ones
            req_headers = {
                h["name"].lower(): h["value"]
                for h in req.get("headers", [])
                if h["name"].lower() in _KEEP_HEADERS
                or (h["name"].lower() not in _NOISE_HEADERS and h["name"].startswith("x-"))
            }

            # Condense response body for preview
            res_text = res_content.get("text", "")
            try:
                # If it's valid JSON, parse it and re-encode minified
                parsed_json = json.loads(res_text)
                res_preview = json.dumps(parsed_json)[:self.max_response_preview]
            except Exception:
                res_preview = res_text[:self.max_response_preview]

            distilled_entry = {
                "method": req.get("method"),
                "url": url,
                "req_headers": req_headers,
                "req_body": req.get("postData", {}).get("text", "") or None,
                "res_status": res.get("status"),
                "res_mime": mime,
                "res_size": res_content.get("size", 0),
                "res_preview": res_preview,
            }
            distilled.append(distilled_entry)

        # Put largest responses first — they're most likely the data payloads
        distilled.sort(key=lambda e: e.get("res_size", 0), reverse=True)

        logger.info(
            f"HAR distilled: {len(entries)} total entries → {len(distilled)} API candidates"
        )
        return distilled

    def estimate_tokens(self, distilled: list) -> int:
        """Rough token estimate for the distilled HAR (4 chars ≈ 1 token)."""
        return len(json.dumps(distilled)) // 4
