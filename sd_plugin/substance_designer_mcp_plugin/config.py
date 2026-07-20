"""Plugin paths and non-secret defaults."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

STATE_DIR = Path.home() / ".substance-designer-mcp"
SESSION_PATH = Path(
    os.getenv("SUBSTANCE_DESIGNER_MCP_SESSION_PATH", str(STATE_DIR / "session.json"))
)
LOG_DIR = STATE_DIR / "logs"
LOG_PATH = Path(os.getenv("SUBSTANCE_DESIGNER_MCP_PLUGIN_LOG_PATH", str(LOG_DIR / "plugin.log")))
PLUGIN_VERSION = "1.1.0"


def bridge_timeouts() -> Tuple[float, float]:
    """Return validated read/write timeouts shared with the external client."""

    read_timeout = float(os.getenv("SUBSTANCE_DESIGNER_MCP_READ_TIMEOUT", "5"))
    write_timeout = float(os.getenv("SUBSTANCE_DESIGNER_MCP_WRITE_TIMEOUT", "30"))
    if min(read_timeout, write_timeout) <= 0:
        raise ValueError("Bridge timeouts must be positive.")
    return read_timeout, write_timeout
