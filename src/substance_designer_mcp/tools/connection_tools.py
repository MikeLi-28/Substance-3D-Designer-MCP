"""Explicit runtime-validated connection tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.references import GraphRef
from substance_designer_mcp.models.responses import BridgeCaller, invoke

from .annotations import WRITE


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    def call(
        command: str,
        graph: GraphRef,
        source_node: str,
        source_property: str,
        target_node: str,
        target_property: str,
    ) -> dict[str, Any]:
        return invoke(
            client,
            command,
            {
                "graph": graph.model_dump(mode="json"),
                "source_node": source_node,
                "source_property": source_property,
                "target_node": target_node,
                "target_property": target_property,
            },
            write=True,
        )

    @mcp.tool(
        name="sd_connect_nodes",
        description=(
            "Connect explicit runtime properties after direction, type, and duplicate checks."
        ),
        annotations=WRITE,
        structured_output=True,
    )
    def sd_connect_nodes(
        graph: GraphRef,
        source_node: str,
        source_property: str,
        target_node: str,
        target_property: str,
    ) -> dict[str, Any]:
        return call(
            "sd_connect_nodes",
            graph,
            source_node,
            source_property,
            target_node,
            target_property,
        )

    @mcp.tool(
        name="sd_disconnect_nodes",
        description="Disconnect one explicit existing property connection.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_disconnect_nodes(
        graph: GraphRef,
        source_node: str,
        source_property: str,
        target_node: str,
        target_property: str,
    ) -> dict[str, Any]:
        return call(
            "sd_disconnect_nodes",
            graph,
            source_node,
            source_property,
            target_node,
            target_property,
        )
