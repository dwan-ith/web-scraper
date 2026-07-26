"""
Pytest shared fixtures
"""
import pytest


@pytest.fixture
def sample_har_entry():
    """A minimal realistic HAR entry representing an XHR API call."""
    return {
        "request": {
            "method": "GET",
            "url": "https://api.example.com/v2/papers?limit=20",
            "headers": [
                {"name": "Authorization", "value": "Bearer eyJhbGci.token"},
                {"name": "Content-Type", "value": "application/json"},
                {"name": "user-agent", "value": "Mozilla/5.0"},
                {"name": "sec-ch-ua", "value": '"Chromium"'},
                {"name": "x-api-version", "value": "2"},
            ],
            "postData": {},
        },
        "response": {
            "status": 200,
            "content": {
                "mimeType": "application/json",
                "size": 4200,
                "text": '{"papers": [{"id": 1, "doi": "10.1234/test", "title": "Test Paper"}]}',
            },
        },
    }


@pytest.fixture
def sample_har(sample_har_entry):
    """Minimal valid .HAR dict with one useful entry and noise."""
    return {
        "log": {
            "entries": [
                sample_har_entry,
                {
                    "request": {
                        "method": "GET",
                        "url": "https://cdn.example.com/logo.png",
                        "headers": [],
                        "postData": {},
                    },
                    "response": {
                        "status": 200,
                        "content": {"mimeType": "image/png", "size": 8000, "text": ""},
                    },
                },
            ]
        }
    }
