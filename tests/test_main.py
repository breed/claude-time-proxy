"""Tests for the main FastAPI application."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from claude_time_proxy.config import Settings
from claude_time_proxy.main import app, set_settings_getter


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        anthropic_api_key="test-key",
        timezone="UTC",
        allowed_days=[0, 1, 2, 3, 4, 5, 6],  # All days allowed for testing
        start_hour=0,
        start_minute=0,
        end_hour=23,
        end_minute=59,
    )


@pytest.fixture
def client(test_settings):
    """Create test client with overridden settings."""
    set_settings_getter(lambda: test_settings)
    with TestClient(app) as c:
        yield c
    set_settings_getter(None)


class TestHealthCheck:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestScheduleEndpoint:
    def test_schedule_returns_status(self, client):
        response = client.get("/schedule")
        assert response.status_code == 200
        data = response.json()
        assert "access_allowed" in data
        assert "timezone" in data


class TestAccessDenied:
    def test_denied_outside_schedule(self):
        # Create settings that deny all access
        deny_settings = Settings(
            anthropic_api_key="test-key",
            timezone="UTC",
            allowed_days=[],  # No days allowed
            start_hour=0,
            start_minute=0,
            end_hour=23,
            end_minute=59,
        )
        set_settings_getter(lambda: deny_settings)
        with TestClient(app) as client:
            response = client.post("/v1/messages", json={})
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]["error"]
        set_settings_getter(None)


class TestBypassKey:
    def test_bypass_key_allows_access(self):
        # Create settings with bypass key that would normally deny access
        bypass_settings = Settings(
            anthropic_api_key="test-key",
            timezone="UTC",
            allowed_days=[],  # No days allowed
            start_hour=0,
            start_minute=0,
            end_hour=23,
            end_minute=59,
            bypass_key="secret-bypass",
        )
        set_settings_getter(lambda: bypass_settings)
        with TestClient(app) as client:
            # Without bypass key - should be denied
            response = client.post("/v1/messages", json={})
            assert response.status_code == 403

            # With wrong bypass key - should be denied
            response = client.post(
                "/v1/messages",
                json={},
                headers={"x-bypass-key": "wrong-key"},
            )
            assert response.status_code == 403

            # With correct bypass key - would proceed (but fail at proxy stage without real API)
            # We patch the proxy_request to verify it gets called
            with patch("claude_time_proxy.main.proxy_request") as mock_proxy:
                mock_proxy.return_value = type("Response", (), {"status_code": 200, "content": b"{}"})()
                response = client.post(
                    "/v1/messages",
                    json={},
                    headers={"x-bypass-key": "secret-bypass"},
                )
                mock_proxy.assert_called_once()
        set_settings_getter(None)
