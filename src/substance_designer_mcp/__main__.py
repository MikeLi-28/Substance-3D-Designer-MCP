"""Console entry point for the stdio MCP server."""

from __future__ import annotations

from substance_designer_mcp.bridge.client import BridgeClient
from substance_designer_mcp.config import Settings
from substance_designer_mcp.logging_config import configure_logging
from substance_designer_mcp.server import build_server


def main() -> None:
    """Start the official MCP SDK using stdio transport."""

    settings = Settings.from_env()
    configure_logging(settings.log_level)
    client = BridgeClient(
        session_path=settings.session_path,
        connect_timeout=settings.connect_timeout,
        read_timeout=settings.read_timeout,
        write_timeout=settings.write_timeout,
    )
    build_server(client).run("stdio")


if __name__ == "__main__":
    main()
