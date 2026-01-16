"""Read Claude CLI credentials for OAuth authentication."""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"
TOKEN_REFRESH_URL = "https://claude.ai/api/auth/renew_access_token"


@dataclass
class ClaudeCredentials:
    """OAuth credentials from Claude CLI."""

    access_token: str
    refresh_token: str
    expires_at: int

    def is_expired(self) -> bool:
        """Check if the access token is expired (with 5 min buffer)."""
        return time.time() > (self.expires_at - 300)


def load_credentials(path: Path | None = None) -> ClaudeCredentials | None:
    """
    Load Claude credentials from the credentials file.

    Args:
        path: Path to credentials file. Defaults to ~/.claude/.credentials.json

    Returns:
        ClaudeCredentials if found, None otherwise.
    """
    creds_path = path or DEFAULT_CREDENTIALS_PATH

    if not creds_path.exists():
        logger.warning(f"Credentials file not found: {creds_path}")
        return None

    try:
        data = json.loads(creds_path.read_text())
        oauth = data.get("claudeAiOauth")
        if not oauth:
            logger.warning("No claudeAiOauth in credentials file")
            return None

        return ClaudeCredentials(
            access_token=oauth["accessToken"],
            refresh_token=oauth["refreshToken"],
            expires_at=oauth["expiresAt"],
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse credentials: {e}")
        return None


def save_credentials(creds: ClaudeCredentials, path: Path | None = None) -> None:
    """Save updated credentials back to the file."""
    creds_path = path or DEFAULT_CREDENTIALS_PATH

    data = {}
    if creds_path.exists():
        data = json.loads(creds_path.read_text())

    data["claudeAiOauth"] = {
        **data.get("claudeAiOauth", {}),
        "accessToken": creds.access_token,
        "refreshToken": creds.refresh_token,
        "expiresAt": creds.expires_at,
    }

    creds_path.write_text(json.dumps(data, indent=2))


def refresh_access_token(creds: ClaudeCredentials) -> ClaudeCredentials | None:
    """
    Refresh the access token using the refresh token.

    Args:
        creds: Current credentials with refresh token.

    Returns:
        New credentials if refresh succeeded, None otherwise.
    """
    try:
        response = httpx.post(
            TOKEN_REFRESH_URL,
            headers={
                "Authorization": f"Bearer {creds.refresh_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        return ClaudeCredentials(
            access_token=data["accessToken"],
            refresh_token=data.get("refreshToken", creds.refresh_token),
            expires_at=data["expiresAt"],
        )
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        return None


def get_valid_access_token(path: Path | None = None) -> str | None:
    """
    Get a valid access token, refreshing if necessary.

    Args:
        path: Path to credentials file.

    Returns:
        Valid access token or None if unavailable.
    """
    creds = load_credentials(path)
    if not creds:
        return None

    if creds.is_expired():
        logger.info("Access token expired, refreshing...")
        new_creds = refresh_access_token(creds)
        if new_creds:
            save_credentials(new_creds, path)
            creds = new_creds
        else:
            logger.error("Failed to refresh token")
            return None

    return creds.access_token
