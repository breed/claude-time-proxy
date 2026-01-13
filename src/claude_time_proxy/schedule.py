"""Time-based access control for the Claude proxy."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from .config import Settings


def is_access_allowed(settings: Settings, now: datetime | None = None) -> bool:
    """
    Check if access is currently allowed based on the configured schedule.

    Args:
        settings: Application settings containing schedule configuration.
        now: Optional datetime for testing. Uses current time if not provided.

    Returns:
        True if access is allowed, False otherwise.
    """
    tz = ZoneInfo(settings.timezone)

    if now is None:
        now = datetime.now(tz)
    else:
        now = now.astimezone(tz)

    # Check day of week
    if now.weekday() not in settings.allowed_days:
        return False

    # Check time window
    current_time = now.time()
    start_time = time(settings.start_hour, settings.start_minute)
    end_time = time(settings.end_hour, settings.end_minute)

    # Handle overnight windows (e.g., 22:00 - 06:00)
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return current_time >= start_time or current_time <= end_time


def get_schedule_status(settings: Settings) -> dict:
    """
    Get human-readable schedule status information.

    Returns:
        Dictionary with current status and schedule details.
    """
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    allowed = is_access_allowed(settings, now)

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    allowed_day_names = [day_names[d] for d in sorted(settings.allowed_days)]

    return {
        "access_allowed": allowed,
        "current_time": now.isoformat(),
        "timezone": settings.timezone,
        "current_day": day_names[now.weekday()],
        "allowed_days": allowed_day_names,
        "time_window": f"{settings.start_hour:02d}:{settings.start_minute:02d} - {settings.end_hour:02d}:{settings.end_minute:02d}",
    }
