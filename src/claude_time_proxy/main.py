"""Main FastAPI application for the Claude time proxy."""

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .credentials import get_valid_access_token
from .proxy import proxy_request
from .schedule import get_schedule_status, is_access_allowed
from .users import get_access_tracker, validate_api_key

# Module-level settings getter that can be replaced for testing
_settings_getter: Callable[[], Settings] | None = None


@lru_cache
def get_cached_settings() -> Settings:
    """Get cached settings instance."""
    if _settings_getter is not None:
        return _settings_getter()
    return get_settings()


def set_settings_getter(getter: Callable[[], Settings] | None) -> None:
    """Set a custom settings getter (for testing)."""
    global _settings_getter
    _settings_getter = getter
    get_cached_settings.cache_clear()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_cached_settings()
    print(f"Claude Time Proxy starting on {settings.host}:{settings.port}")
    print(f"Schedule file: {settings.schedule_file}")
    print(f"Users file: {settings.users_file}")
    if settings.use_claude_credentials:
        print("Auth mode: Claude CLI credentials (~/.claude/.credentials.json)")
    else:
        print("Auth mode: Anthropic API key")
    yield
    # Log end of sessions for all users when shutting down
    tracker = get_access_tracker()
    for email in list(tracker.sessions.keys()):
        tracker.log_session_end(email)
    tracker.reset_all_sessions()
    print("Claude Time Proxy shutting down")


app = FastAPI(
    title="Claude Time Proxy",
    description="A time-based access control proxy for Claude API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/schedule")
async def schedule_status():
    """Get current schedule status."""
    settings = get_cached_settings()
    return get_schedule_status(settings.schedule_file)


def check_access(settings: Settings) -> None:
    """
    Check if access is allowed based on schedule file.

    Raises:
        HTTPException: If access is denied.
    """
    if not is_access_allowed(settings.schedule_file):
        # Log end of sessions for all users when access period ends
        tracker = get_access_tracker()
        for email in list(tracker.sessions.keys()):
            tracker.log_session_end(email)
        tracker.reset_all_sessions()

        status = get_schedule_status(settings.schedule_file)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied outside of allowed schedule",
                "schedule": status,
            },
        )


def check_user(request: Request, settings: Settings) -> str:
    """
    Validate the user's API key.

    Args:
        request: The incoming request.
        settings: Application settings.

    Returns:
        The user's email if valid.

    Raises:
        HTTPException: If the API key is invalid.
    """
    api_key = request.headers.get("x-api-key") or request.headers.get("authorization", "").replace("Bearer ", "")

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "Missing API key"},
        )

    user = validate_api_key(settings.users_file, api_key)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid API key"},
        )

    return user.email


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_v1(request: Request, path: str) -> Response:
    """Proxy requests to Claude API v1 endpoints."""
    settings = get_cached_settings()
    check_access(settings)
    user_email = check_user(request, settings)

    # Record access for the user
    tracker = get_access_tracker()
    tracker.record_access(user_email)

    # Get authentication credentials
    access_token = None
    api_key = None

    if settings.use_claude_credentials:
        access_token = get_valid_access_token()
        if not access_token:
            raise HTTPException(
                status_code=503,
                detail={"error": "Failed to get valid Claude credentials. Try running 'claude' to refresh login."},
            )
    else:
        api_key = settings.anthropic_api_key

    return await proxy_request(
        request=request,
        target_base_url=settings.anthropic_base_url,
        path=f"v1/{path}",
        api_key=api_key,
        access_token=access_token,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


def run():
    """Run the proxy server."""
    import uvicorn

    settings = get_cached_settings()
    uvicorn.run(
        "claude_time_proxy.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
