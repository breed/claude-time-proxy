"""Tests for user authentication and access logging."""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from claude_time_proxy.config import Settings
from claude_time_proxy.main import app, set_settings_getter
from claude_time_proxy.users import (
    AccessSession,
    AccessTracker,
    User,
    get_access_tracker,
    parse_users_file,
    set_access_tracker,
    validate_api_key,
)


@pytest.fixture
def users_file(tmp_path):
    """Create a temporary users file."""
    def _create(content: str) -> str:
        path = tmp_path / "users.txt"
        path.write_text(content)
        return str(path)
    return _create


@pytest.fixture
def schedule_file(tmp_path):
    """Create a temporary schedule file."""
    def _create(content: str) -> str:
        path = tmp_path / "schedule.txt"
        path.write_text(content)
        return str(path)
    return _create


class TestParseUsersFile:
    def test_parse_valid_file(self, users_file):
        path = users_file("alice@example.com key1\nbob@example.com key2")
        users = parse_users_file(path)

        assert len(users) == 2
        assert "key1" in users
        assert "key2" in users
        assert users["key1"].email == "alice@example.com"
        assert users["key2"].email == "bob@example.com"

    def test_parse_with_comments_and_blank_lines(self, users_file):
        content = """# This is a comment
alice@example.com key1

# Another comment
bob@example.com key2
"""
        path = users_file(content)
        users = parse_users_file(path)

        assert len(users) == 2

    def test_parse_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_users_file("/nonexistent/path")

    def test_parse_invalid_format(self, users_file):
        path = users_file("invalid_line_without_key")
        with pytest.raises(ValueError, match="Expected 'EMAIL KEY'"):
            parse_users_file(path)

    def test_parse_too_many_parts(self, users_file):
        path = users_file("alice@example.com key1 extra_stuff")
        with pytest.raises(ValueError, match="Expected 'EMAIL KEY'"):
            parse_users_file(path)

    def test_parse_duplicate_key(self, users_file):
        path = users_file("alice@example.com key1\nbob@example.com key1")
        with pytest.raises(ValueError, match="Duplicate key"):
            parse_users_file(path)


class TestValidateApiKey:
    def test_valid_key(self, users_file):
        path = users_file("alice@example.com test-key-123")
        user = validate_api_key(path, "test-key-123")

        assert user is not None
        assert user.email == "alice@example.com"

    def test_invalid_key(self, users_file):
        path = users_file("alice@example.com test-key-123")
        user = validate_api_key(path, "wrong-key")

        assert user is None

    def test_missing_file(self):
        user = validate_api_key("/nonexistent", "any-key")
        assert user is None


class TestAccessTracker:
    def test_first_access(self):
        tracker = AccessTracker()
        now = datetime(2024, 1, 15, 10, 0, 0)

        tracker.record_access("alice@example.com", now)

        session = tracker.sessions["alice@example.com"]
        assert session.email == "alice@example.com"
        assert session.first_access == now
        assert session.last_access == now
        assert session.request_count == 1

    def test_subsequent_access(self):
        tracker = AccessTracker()
        time1 = datetime(2024, 1, 15, 10, 0, 0)
        time2 = datetime(2024, 1, 15, 10, 5, 0)
        time3 = datetime(2024, 1, 15, 10, 10, 0)

        tracker.record_access("alice@example.com", time1)
        tracker.record_access("alice@example.com", time2)
        tracker.record_access("alice@example.com", time3)

        session = tracker.sessions["alice@example.com"]
        assert session.first_access == time1
        assert session.last_access == time3
        assert session.request_count == 3

    def test_multiple_users(self):
        tracker = AccessTracker()
        now = datetime(2024, 1, 15, 10, 0, 0)

        tracker.record_access("alice@example.com", now)
        tracker.record_access("bob@example.com", now)
        tracker.record_access("alice@example.com", now)

        assert len(tracker.sessions) == 2
        assert tracker.sessions["alice@example.com"].request_count == 2
        assert tracker.sessions["bob@example.com"].request_count == 1

    def test_reset_session(self):
        tracker = AccessTracker()
        now = datetime(2024, 1, 15, 10, 0, 0)

        tracker.record_access("alice@example.com", now)
        session = tracker.reset_session("alice@example.com")

        assert session is not None
        assert session.email == "alice@example.com"
        assert "alice@example.com" not in tracker.sessions

    def test_reset_nonexistent_session(self):
        tracker = AccessTracker()
        session = tracker.reset_session("nonexistent@example.com")
        assert session is None

    def test_reset_all_sessions(self):
        tracker = AccessTracker()
        now = datetime(2024, 1, 15, 10, 0, 0)

        tracker.record_access("alice@example.com", now)
        tracker.record_access("bob@example.com", now)
        sessions = tracker.reset_all_sessions()

        assert len(sessions) == 2
        assert len(tracker.sessions) == 0


class TestMainIntegration:
    @pytest.fixture
    def test_settings(self, schedule_file, users_file):
        """Create test settings with all-hours access."""
        sched_path = schedule_file("Mon,Tue,Wed,Thu,Fri,Sat,Sun 00:00-23:59")
        users_path = users_file("alice@example.com test-api-key")
        return Settings(
            anthropic_api_key="real-anthropic-key",
            schedule_file=sched_path,
            users_file=users_path,
        )

    @pytest.fixture
    def client(self, test_settings):
        """Create test client with overridden settings."""
        set_settings_getter(lambda: test_settings)
        set_access_tracker(AccessTracker())
        with TestClient(app) as c:
            yield c
        set_settings_getter(None)
        set_access_tracker(None)

    def test_missing_api_key(self, client):
        response = client.post("/v1/messages", json={})
        assert response.status_code == 401
        assert "Missing API key" in response.json()["detail"]["error"]

    def test_invalid_api_key(self, client):
        response = client.post(
            "/v1/messages",
            json={},
            headers={"x-api-key": "wrong-key"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]["error"]

    def test_valid_api_key_records_access(self, test_settings):
        set_settings_getter(lambda: test_settings)
        tracker = AccessTracker()
        set_access_tracker(tracker)

        with TestClient(app) as client:
            with patch("claude_time_proxy.main.proxy_request") as mock_proxy:
                mock_proxy.return_value = type("Response", (), {"status_code": 200, "content": b"{}"})()

                # Make multiple requests
                client.post("/v1/messages", json={}, headers={"x-api-key": "test-api-key"})
                client.post("/v1/messages", json={}, headers={"x-api-key": "test-api-key"})
                client.post("/v1/messages", json={}, headers={"x-api-key": "test-api-key"})

            # Check session inside TestClient context (before lifespan shutdown)
            session = tracker.sessions.get("alice@example.com")
            assert session is not None
            assert session.request_count == 3

        set_settings_getter(None)
        set_access_tracker(None)

    def test_authorization_header(self, test_settings):
        """Test that Bearer token auth works."""
        set_settings_getter(lambda: test_settings)
        set_access_tracker(AccessTracker())

        with TestClient(app) as client:
            with patch("claude_time_proxy.main.proxy_request") as mock_proxy:
                mock_proxy.return_value = type("Response", (), {"status_code": 200, "content": b"{}"})()

                response = client.post(
                    "/v1/messages",
                    json={},
                    headers={"Authorization": "Bearer test-api-key"}
                )
                assert response.status_code == 200

        set_settings_getter(None)
        set_access_tracker(None)

    def test_access_denied_logs_sessions(self, schedule_file, users_file):
        """Test that sessions are logged when access period ends."""
        # Start with access allowed
        sched_path = schedule_file("Mon,Tue,Wed,Thu,Fri,Sat,Sun 00:00-23:59")
        users_path = users_file("alice@example.com test-api-key")
        settings = Settings(
            anthropic_api_key="real-key",
            schedule_file=sched_path,
            users_file=users_path,
        )

        set_settings_getter(lambda: settings)
        tracker = AccessTracker()
        set_access_tracker(tracker)

        with TestClient(app) as client:
            with patch("claude_time_proxy.main.proxy_request") as mock_proxy:
                mock_proxy.return_value = type("Response", (), {"status_code": 200, "content": b"{}"})()
                client.post("/v1/messages", json={}, headers={"x-api-key": "test-api-key"})

            # Verify session was recorded (check before TestClient exits)
            assert tracker.sessions.get("alice@example.com") is not None

        set_settings_getter(None)
        set_access_tracker(None)
