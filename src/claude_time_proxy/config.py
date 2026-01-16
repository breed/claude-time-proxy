"""Configuration management for the Claude time proxy."""

import sys

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLAUDE_PROXY_",
    )

    # Claude API configuration
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key (optional if use_claude_credentials=True)",
    )
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com",
        description="Anthropic API base URL",
    )

    # Use Claude CLI credentials (~/.claude/.credentials.json)
    use_claude_credentials: bool = Field(
        default=True,
        description="Use OAuth credentials from Claude CLI instead of API key",
    )

    # Proxy server configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080)

    # Schedule configuration file path
    schedule_file: str = Field(
        default="schedule.txt",
        description="Path to schedule configuration file",
    )

    # Users configuration file path
    users_file: str = Field(
        default="users.txt",
        description="Path to users configuration file",
    )


def get_settings() -> Settings:
    """Load and return application settings."""
    settings = Settings()

    if not settings.anthropic_api_key and not settings.use_claude_credentials:
        print(
            "Error: No authentication configured.\n"
            "\n"
            "Either set an API key:\n"
            "  export CLAUDE_PROXY_ANTHROPIC_API_KEY=sk-ant-...\n"
            "\n"
            "Or use Claude CLI credentials:\n"
            "  export CLAUDE_PROXY_USE_CLAUDE_CREDENTIALS=true\n",
            file=sys.stderr,
        )
        sys.exit(1)

    return settings
