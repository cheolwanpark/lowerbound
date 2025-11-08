"""Configuration settings loaded from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    claude_code_oauth_token: str
    backend_api_url: str
    redis_url: str
    queue_name: str
    max_workers: int
    agent_timeout_seconds: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            claude_code_oauth_token=os.getenv("CLAUDE_CODE_OAUTH_TOKEN", ""),
            backend_api_url=os.getenv("BACKEND_API_URL", "http://localhost:8000"),
            redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            queue_name=os.getenv("QUEUE_NAME", "chat-agent"),
            max_workers=int(os.getenv("MAX_WORKERS", "10")),
            agent_timeout_seconds=int(os.getenv("AGENT_TIMEOUT_SECONDS", "60")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def validate(self) -> None:
        """Validate required settings."""
        if not self.claude_code_oauth_token:
            raise ValueError("CLAUDE_CODE_OAUTH_TOKEN environment variable is required")

        if self.agent_timeout_seconds < 1:
            raise ValueError("AGENT_TIMEOUT_SECONDS must be >= 1")
