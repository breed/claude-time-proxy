"""Main FastAPI application for the Claude time proxy."""

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .proxy import proxy_request
from .schedule import get_schedule_status, is_access_allowed

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
    yield
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
        status = get_schedule_status(settings.schedule_file)
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied outside of allowed schedule",
                "schedule": status,
            },
        )


@app.api_route("/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_v1(request: Request, path: str) -> Response:
    """Proxy requests to Claude API v1 endpoints."""
    settings = get_cached_settings()
    check_access(settings)

    return await proxy_request(
        request=request,
        target_base_url=settings.anthropic_base_url,
        api_key=settings.anthropic_api_key,
        path=f"v1/{path}",
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
