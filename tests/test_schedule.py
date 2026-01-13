"""Tests for schedule-based access control."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from claude_time_proxy.config import Settings
from claude_time_proxy.schedule import is_access_allowed, get_schedule_status


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        anthropic_api_key="test-key",
        timezone="UTC",
        allowed_days=[0, 1, 2, 3, 4],  # Monday-Friday
        start_hour=9,
        start_minute=0,
        end_hour=17,
        end_minute=0,
    )


class TestIsAccessAllowed:
    def test_allowed_weekday_within_hours(self, settings):
        # Wednesday at 12:00 UTC
        dt = datetime(2024, 1, 10, 12, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is True

    def test_denied_weekday_before_hours(self, settings):
        # Wednesday at 8:00 UTC
        dt = datetime(2024, 1, 10, 8, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is False

    def test_denied_weekday_after_hours(self, settings):
        # Wednesday at 18:00 UTC
        dt = datetime(2024, 1, 10, 18, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is False

    def test_denied_weekend(self, settings):
        # Saturday at 12:00 UTC
        dt = datetime(2024, 1, 13, 12, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is False

    def test_allowed_at_start_time(self, settings):
        # Wednesday at exactly 9:00 UTC
        dt = datetime(2024, 1, 10, 9, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is True

    def test_allowed_at_end_time(self, settings):
        # Wednesday at exactly 17:00 UTC
        dt = datetime(2024, 1, 10, 17, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is True


class TestOvernightWindow:
    def test_overnight_window_late_evening(self):
        settings = Settings(
            anthropic_api_key="test-key",
            timezone="UTC",
            allowed_days=[0, 1, 2, 3, 4],
            start_hour=22,
            start_minute=0,
            end_hour=6,
            end_minute=0,
        )
        # Wednesday at 23:00 UTC
        dt = datetime(2024, 1, 10, 23, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is True

    def test_overnight_window_early_morning(self):
        settings = Settings(
            anthropic_api_key="test-key",
            timezone="UTC",
            allowed_days=[0, 1, 2, 3, 4],
            start_hour=22,
            start_minute=0,
            end_hour=6,
            end_minute=0,
        )
        # Wednesday at 5:00 UTC
        dt = datetime(2024, 1, 10, 5, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is True

    def test_overnight_window_midday_denied(self):
        settings = Settings(
            anthropic_api_key="test-key",
            timezone="UTC",
            allowed_days=[0, 1, 2, 3, 4],
            start_hour=22,
            start_minute=0,
            end_hour=6,
            end_minute=0,
        )
        # Wednesday at 12:00 UTC
        dt = datetime(2024, 1, 10, 12, 0, tzinfo=ZoneInfo("UTC"))
        assert is_access_allowed(settings, dt) is False


class TestGetScheduleStatus:
    def test_returns_expected_keys(self, settings):
        status = get_schedule_status(settings)
        assert "access_allowed" in status
        assert "current_time" in status
        assert "timezone" in status
        assert "current_day" in status
        assert "allowed_days" in status
        assert "time_window" in status
