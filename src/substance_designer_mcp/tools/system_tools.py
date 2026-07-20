"""System status and capability MCP tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.responses import BridgeCaller, invoke, invoke_ping

from .annotations import READ_ONLY


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    @mcp.tool(
        name="sd_ping",
        description=(
            "Report MCP, bridge, plugin, Designer version, session, and compatibility status."
        ),
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_ping() -> dict[str, Any]:
        return invoke_ping(client)

    @mcp.tool(
        name="sd_get_application_info",
        description=(
            "Read Designer version, Python, platform, open packages, graph, and capabilities."
        ),
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_get_application_info() -> dict[str, Any]:
        return invoke(client, "sd_get_application_info", {})

    @mcp.tool(
        name="sd_get_capabilities",
        description="Read the runtime-probed capability matrix and verification status.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_get_capabilities() -> dict[str, Any]:
        return invoke(client, "sd_get_capabilities", {})
