"""Configuration management for the Claude time proxy."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Schedule configuration file path
    schedule_file: str = Field(
        default="schedule.txt",
        description="Path to schedule configuration file",
    )


def get_settings() -> Settings:
    """Load and return application settings."""
    return Settings()
