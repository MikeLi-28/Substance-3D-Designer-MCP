"""Environment-configurable external server settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from substance_designer_mcp.bridge.discovery import DEFAULT_SESSION_PATH


@dataclass(frozen=True)
class Settings:
    session_path: Path = DEFAULT_SESSION_PATH
    connect_timeout: float = 5.0
    read_timeout: float = 5.0
    write_timeout: float = 30.0
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        """Read documented environment variables and validate their bounds."""

        settings = cls(
            session_path=Path(
                os.getenv("SUBSTANCE_DESIGNER_MCP_SESSION_PATH", str(DEFAULT_SESSION_PATH))
            ).expanduser(),
            connect_timeout=float(os.getenv("SUBSTANCE_DESIGNER_MCP_CONNECT_TIMEOUT", "5")),
            read_timeout=float(os.getenv("SUBSTANCE_DESIGNER_MCP_READ_TIMEOUT", "5")),
            write_timeout=float(os.getenv("SUBSTANCE_DESIGNER_MCP_WRITE_TIMEOUT", "30")),
            log_level=os.getenv("SUBSTANCE_DESIGNER_MCP_LOG_LEVEL", "INFO").upper(),
        )
        if min(settings.connect_timeout, settings.read_timeout, settings.write_timeout) <= 0:
            raise ValueError("Bridge timeouts must be positive.")
        if settings.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("SUBSTANCE_DESIGNER_MCP_LOG_LEVEL is invalid.")
        return settings
