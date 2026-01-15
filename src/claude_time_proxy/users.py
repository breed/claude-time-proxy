"""User authentication and access logging for the Claude proxy."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class User:
    """A user with their associated API key."""

    email: str
    key: str


@dataclass
class AccessSession:
    """Tracks a user's access within a time period."""

    email: str
    first_access: datetime
    last_access: datetime
    request_count: int = 0


@dataclass
class AccessTracker:
    """Tracks user accesses within time periods."""

    sessions: dict[str, AccessSession] = field(default_factory=dict)

    def record_access(self, email: str, now: datetime | None = None) -> None:
        """
        Record an access for a user.

        Args:
            email: The user's email.
            now: Optional datetime for testing.
        """
        if now is None:
            now = datetime.now()

        if email not in self.sessions:
            # First access in this time period
            self.sessions[email] = AccessSession(
                email=email,
                first_access=now,
                last_access=now,
                request_count=1,
            )
            logger.info(f"First access for user {email} at {now.isoformat()}")
        else:
            session = self.sessions[email]
            session.last_access = now
            session.request_count += 1

    def reset_session(self, email: str) -> AccessSession | None:
        """
        Reset a user's session and return the final session data.

        Args:
            email: The user's email.

        Returns:
            The session data before reset, or None if no session existed.
        """
        return self.sessions.pop(email, None)

    def reset_all_sessions(self) -> dict[str, AccessSession]:
        """
        Reset all sessions and return the final session data.

        Returns:
            Dictionary of all sessions before reset.
        """
        sessions = self.sessions.copy()
        self.sessions.clear()
        return sessions

    def log_session_end(self, email: str) -> None:
        """Log the end of a user's session with request count."""
        session = self.sessions.get(email)
        if session:
            logger.info(
                f"Last access for user {email} at {session.last_access.isoformat()}, "
                f"total requests: {session.request_count}"
            )


def parse_users_file(file_path: str) -> dict[str, User]:
    """
    Parse a users configuration file.

    Format:
        # Comment lines start with #
        user@example.com their_random_api_key
        another@example.com another_key

    Args:
        file_path: Path to the users file.

    Returns:
        Dictionary mapping API keys to User objects.

    Raises:
        FileNotFoundError: If the users file doesn't exist.
        ValueError: If the file contains invalid syntax.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Users file not found: {file_path}")

    users_by_key: dict[str, User] = {}

    for line_num, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Split into email and key
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(
                f"Line {line_num}: Expected 'EMAIL KEY', got: {line}"
            )

        email, key = parts

        if key in users_by_key:
            raise ValueError(
                f"Line {line_num}: Duplicate key for user {email}"
            )

        users_by_key[key] = User(email=email, key=key)

    return users_by_key


def validate_api_key(users_file: str, api_key: str) -> User | None:
    """
    Validate an API key against the users file.

    Args:
        users_file: Path to the users file.
        api_key: The API key to validate.

    Returns:
        The User if valid, None otherwise.
    """
    try:
        users = parse_users_file(users_file)
    except FileNotFoundError:
        logger.warning(f"Users file not found: {users_file}")
        return None

    return users.get(api_key)


# Global access tracker instance
_access_tracker: AccessTracker | None = None


def get_access_tracker() -> AccessTracker:
    """Get the global access tracker instance."""
    global _access_tracker
    if _access_tracker is None:
        _access_tracker = AccessTracker()
    return _access_tracker


def set_access_tracker(tracker: AccessTracker | None) -> None:
    """Set the global access tracker (for testing)."""
    global _access_tracker
    _access_tracker = tracker
