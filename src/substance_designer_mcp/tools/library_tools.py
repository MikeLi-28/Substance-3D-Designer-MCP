"""Loaded-package library search tool."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.responses import BridgeCaller, invoke

from .annotations import READ_ONLY


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    @mcp.tool(
        name="sd_search_library",
        description=(
            "Search resources in currently loaded packages without UI scraping or guessed URLs."
        ),
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_search_library(
        query: str = "",
        identifier: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {"query": query, "category": category, "limit": limit}
        if identifier is not None:
            arguments["identifier"] = identifier
        return invoke(client, "sd_search_library", arguments)
