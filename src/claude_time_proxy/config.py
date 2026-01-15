"""Configuration management for the Claude time proxy."""

import sys

from pydantic import Field, ValidationError
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

    # Users configuration file path
    users_file: str = Field(
        default="users.txt",
        description="Path to users configuration file",
    )


def get_settings() -> Settings:
    """Load and return application settings."""
    try:
        return Settings()
    except ValidationError as e:
        for error in e.errors():
            if error["loc"] == ("anthropic_api_key",):
                print(
                    "Error: CLAUDE_PROXY_ANTHROPIC_API_KEY environment variable is required.\n"
                    "\n"
                    "Set it in your environment or in a .env file:\n"
                    "  export CLAUDE_PROXY_ANTHROPIC_API_KEY=sk-ant-...\n",
                    file=sys.stderr,
                )
                sys.exit(1)
        raise
