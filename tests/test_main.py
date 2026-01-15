"""Tests for the main FastAPI application."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from claude_time_proxy.config import Settings
from claude_time_proxy.main import app, set_settings_getter
from claude_time_proxy.users import AccessTracker, set_access_tracker


@pytest.fixture
def schedule_file(tmp_path):
    """Create a temporary schedule file."""
    def _create(content: str) -> str:
        path = tmp_path / "schedule.txt"
        path.write_text(content)
        return str(path)
    return _create


@pytest.fixture
def users_file(tmp_path):
    """Create a temporary users file."""
    def _create(content: str) -> str:
        path = tmp_path / "users.txt"
        path.write_text(content)
        return str(path)
    return _create


@pytest.fixture
def test_settings(schedule_file, users_file):
    """Create test settings with all-hours access."""
    sched_path = schedule_file("Mon,Tue,Wed,Thu,Fri,Sat,Sun 00:00-23:59")
    users_path = users_file("test@example.com test-api-key")
    return Settings(
        anthropic_api_key="test-key",
        schedule_file=sched_path,
        users_file=users_path,
    )


@pytest.fixture
def client(test_settings):
    """Create test client with overridden settings."""
    set_settings_getter(lambda: test_settings)
    set_access_tracker(AccessTracker())
    with TestClient(app) as c:
        yield c
    set_settings_getter(None)
    set_access_tracker(None)


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
        assert "rules" in data


class TestAccessDenied:
    def test_denied_outside_schedule(self, schedule_file):
        # Create settings with no access (empty rules)
        path = schedule_file("# No rules - access denied")
        deny_settings = Settings(
            anthropic_api_key="test-key",
            schedule_file=path,
        )
        set_settings_getter(lambda: deny_settings)
        with TestClient(app) as client:
            response = client.post("/v1/messages", json={})
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]["error"]
        set_settings_getter(None)


class TestProxyEndpoint:
    def test_proxy_forwards_request(self, test_settings):
        set_settings_getter(lambda: test_settings)
        set_access_tracker(AccessTracker())
        with TestClient(app) as client:
            with patch("claude_time_proxy.main.proxy_request") as mock_proxy:
                mock_proxy.return_value = type("Response", (), {"status_code": 200, "content": b"{}"})()
                response = client.post(
                    "/v1/messages",
                    json={},
                    headers={"x-api-key": "test-api-key"}
                )
                mock_proxy.assert_called_once()
        set_settings_getter(None)
        set_access_tracker(None)
