"""Tests for schedule-based access control."""

from datetime import datetime, time
from pathlib import Path

import pytest

from claude_time_proxy.schedule import (
    TimeRule,
    is_access_allowed,
    get_schedule_status,
    parse_schedule_file,
)


@pytest.fixture
def schedule_file(tmp_path):
    """Create a temporary schedule file."""
    def _create(content: str) -> str:
        path = tmp_path / "schedule.txt"
        path.write_text(content)
        return str(path)
    return _create


class TestParseScheduleFile:
    def test_parse_weekday_schedule(self, schedule_file):
        path = schedule_file("Mon,Tue,Wed,Thu,Fri 09:00-17:00")
        rules = parse_schedule_file(path)
        assert len(rules) == 1
        assert rules[0].days == {0, 1, 2, 3, 4}
        assert rules[0].start_time == time(9, 0)
        assert rules[0].end_time == time(17, 0)

    def test_parse_multiple_rules(self, schedule_file):
        path = schedule_file("Mon,Tue,Wed,Thu,Fri 09:00-17:00\nSat 10:00-14:00")
        rules = parse_schedule_file(path)
        assert len(rules) == 2

    def test_skip_comments(self, schedule_file):
        path = schedule_file("# This is a comment\nMon 09:00-17:00")
        rules = parse_schedule_file(path)
        assert len(rules) == 1

    def test_skip_blank_lines(self, schedule_file):
        path = schedule_file("Mon 09:00-17:00\n\nTue 09:00-17:00")
        rules = parse_schedule_file(path)
        assert len(rules) == 2

    def test_invalid_day(self, schedule_file):
        path = schedule_file("Monday 09:00-17:00")
        with pytest.raises(ValueError, match="Invalid day"):
            parse_schedule_file(path)

    def test_invalid_time_format(self, schedule_file):
        path = schedule_file("Mon 9:00-17:00")
        with pytest.raises(ValueError, match="Invalid time range"):
            parse_schedule_file(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_schedule_file("/nonexistent/path/schedule.txt")


class TestTimeRule:
    def test_matches_weekday_within_hours(self):
        rule = TimeRule(days={0, 1, 2, 3, 4}, start_time=time(9, 0), end_time=time(17, 0))
        # Wednesday at 12:00
        dt = datetime(2024, 1, 10, 12, 0)
        assert rule.matches(dt) is True

    def test_no_match_wrong_day(self):
        rule = TimeRule(days={0, 1, 2, 3, 4}, start_time=time(9, 0), end_time=time(17, 0))
        # Saturday at 12:00
        dt = datetime(2024, 1, 13, 12, 0)
        assert rule.matches(dt) is False

    def test_no_match_before_hours(self):
        rule = TimeRule(days={0, 1, 2, 3, 4}, start_time=time(9, 0), end_time=time(17, 0))
        # Wednesday at 8:00
        dt = datetime(2024, 1, 10, 8, 0)
        assert rule.matches(dt) is False

    def test_no_match_after_hours(self):
        rule = TimeRule(days={0, 1, 2, 3, 4}, start_time=time(9, 0), end_time=time(17, 0))
        # Wednesday at 18:00
        dt = datetime(2024, 1, 10, 18, 0)
        assert rule.matches(dt) is False

    def test_overnight_window_late_evening(self):
        rule = TimeRule(days={0, 1, 2, 3, 4}, start_time=time(22, 0), end_time=time(6, 0))
        # Wednesday at 23:00
        dt = datetime(2024, 1, 10, 23, 0)
        assert rule.matches(dt) is True

    def test_overnight_window_early_morning(self):
        rule = TimeRule(days={0, 1, 2, 3, 4}, start_time=time(22, 0), end_time=time(6, 0))
        # Wednesday at 5:00
        dt = datetime(2024, 1, 10, 5, 0)
        assert rule.matches(dt) is True

    def test_overnight_window_midday_denied(self):
        rule = TimeRule(days={0, 1, 2, 3, 4}, start_time=time(22, 0), end_time=time(6, 0))
        # Wednesday at 12:00
        dt = datetime(2024, 1, 10, 12, 0)
        assert rule.matches(dt) is False


class TestIsAccessAllowed:
    def test_allowed_when_rule_matches(self, schedule_file):
        path = schedule_file("Mon,Tue,Wed,Thu,Fri,Sat,Sun 00:00-23:59")
        assert is_access_allowed(path) is True

    def test_denied_when_no_rules(self, schedule_file):
        path = schedule_file("# Only comments")
        # No rules means no access
        dt = datetime(2024, 1, 10, 12, 0)
        assert is_access_allowed(path, dt) is False

    def test_denied_when_file_missing(self, tmp_path):
        path = str(tmp_path / "nonexistent.txt")
        assert is_access_allowed(path) is False


class TestGetScheduleStatus:
    def test_returns_expected_keys(self, schedule_file):
        path = schedule_file("Mon,Tue,Wed,Thu,Fri 09:00-17:00")
        status = get_schedule_status(path)
        assert "access_allowed" in status
        assert "current_time" in status
        assert "current_day" in status
        assert "rules" in status

    def test_rules_formatted_correctly(self, schedule_file):
        path = schedule_file("Mon,Tue 09:00-17:00")
        status = get_schedule_status(path)
        assert len(status["rules"]) == 1
        assert status["rules"][0]["days"] == ["Monday", "Tuesday"]
        assert status["rules"][0]["time_window"] == "09:00-17:00"
