"""Time-based access control for the Claude proxy."""

import re
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path

DAY_MAP = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class TimeRule:
    """A single schedule rule specifying allowed days and time range."""

    days: set[int]  # 0=Monday, 6=Sunday
    start_time: time
    end_time: time

    def matches(self, dt: datetime) -> bool:
        """Check if the given datetime matches this rule."""
        if dt.weekday() not in self.days:
            return False

        current_time = dt.time()

        # Handle overnight windows (e.g., 22:00-06:00)
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        else:
            return current_time >= self.start_time or current_time <= self.end_time


def parse_schedule_file(file_path: str) -> list[TimeRule]:
    """
    Parse a schedule configuration file.

    Format:
        # Comment lines start with #
        Mon,Tue,Wed,Thu,Fri 09:00-17:00
        Sat 10:00-14:00

    Args:
        file_path: Path to the schedule file.

    Returns:
        List of TimeRule objects.

    Raises:
        FileNotFoundError: If the schedule file doesn't exist.
        ValueError: If the file contains invalid syntax.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Schedule file not found: {file_path}")

    rules = []
    time_pattern = re.compile(r"^(\d{2}):(\d{2})-(\d{2}):(\d{2})$")

    for line_num, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Split into days and time range
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(
                f"Line {line_num}: Expected 'DAYS HH:MM-HH:MM', got: {line}"
            )

        days_str, time_range = parts

        # Parse days
        days = set()
        for day_str in days_str.split(","):
            day_lower = day_str.strip().lower()
            if day_lower not in DAY_MAP:
                raise ValueError(
                    f"Line {line_num}: Invalid day '{day_str}'. "
                    f"Valid days: Mon, Tue, Wed, Thu, Fri, Sat, Sun"
                )
            days.add(DAY_MAP[day_lower])

        # Parse time range
        match = time_pattern.match(time_range)
        if not match:
            raise ValueError(
                f"Line {line_num}: Invalid time range '{time_range}'. "
                f"Expected format: HH:MM-HH:MM"
            )

        start_hour, start_min, end_hour, end_min = map(int, match.groups())

        try:
            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)
        except ValueError as e:
            raise ValueError(f"Line {line_num}: Invalid time: {e}")

        rules.append(TimeRule(days=days, start_time=start_time, end_time=end_time))

    return rules


def is_access_allowed(schedule_file: str, now: datetime | None = None) -> bool:
    """
    Check if access is currently allowed based on the schedule file.

    Args:
        schedule_file: Path to the schedule configuration file.
        now: Optional datetime for testing. Uses current local time if not provided.

    Returns:
        True if access is allowed, False otherwise.
    """
    if now is None:
        now = datetime.now()

    try:
        rules = parse_schedule_file(schedule_file)
    except FileNotFoundError:
        # No schedule file = no access
        return False

    # Access is allowed if any rule matches
    return any(rule.matches(now) for rule in rules)


def get_schedule_status(schedule_file: str) -> dict:
    """
    Get human-readable schedule status information.

    Returns:
        Dictionary with current status and schedule details.
    """
    now = datetime.now()
    allowed = is_access_allowed(schedule_file, now)

    try:
        rules = parse_schedule_file(schedule_file)
        schedule_rules = []
        for rule in rules:
            day_names = [DAY_NAMES[d] for d in sorted(rule.days)]
            time_window = f"{rule.start_time.strftime('%H:%M')}-{rule.end_time.strftime('%H:%M')}"
            schedule_rules.append({"days": day_names, "time_window": time_window})
    except FileNotFoundError:
        schedule_rules = []

    return {
        "access_allowed": allowed,
        "current_time": now.isoformat(),
        "current_day": DAY_NAMES[now.weekday()],
        "rules": schedule_rules,
    }
