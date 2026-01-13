"""Configuration management for the Claude time proxy."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TimeWindow(BaseSettings):
    """A time window when the proxy is accessible."""

    days: list[int] = Field(
        default=[0, 1, 2, 3, 4],
        description="Days of week (0=Monday, 6=Sunday)",
    )
    start_hour: int = Field(default=9, ge=0, le=23)
    start_minute: int = Field(default=0, ge=0, le=59)
    end_hour: int = Field(default=17, ge=0, le=23)
    end_minute: int = Field(default=0, ge=0, le=59)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLAUDE_PROXY_",
    )

    # Claude API configuration
    anthropic_api_key: str = Field(description="Anthropic API key")
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com",
        description="Anthropic API base URL",
    )

    # Proxy server configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)

    # Time-based access control
    timezone: str = Field(default="UTC", description="Timezone for schedule evaluation")
    allowed_days: list[int] = Field(
        default=[0, 1, 2, 3, 4],
        description="Days of week when access is allowed (0=Monday, 6=Sunday)",
    )
    start_hour: int = Field(default=9, ge=0, le=23, description="Start hour (24h format)")
    start_minute: int = Field(default=0, ge=0, le=59)
    end_hour: int = Field(default=17, ge=0, le=23, description="End hour (24h format)")
    end_minute: int = Field(default=0, ge=0, le=59)

    # Optional: bypass key for emergency access
    bypass_key: str | None = Field(default=None, description="Key to bypass time restrictions")


def get_settings() -> Settings:
    """Load and return application settings."""
    return Settings()
