"""Active graph and bounded graph node read tools."""

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.references import GraphRef
from substance_designer_mcp.models.responses import BridgeCaller, invoke

from .annotations import READ_ONLY


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    @mcp.tool(
        name="sd_get_active_graph",
        description="Read the current editable graph, package, node count, and selection count.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_get_active_graph() -> dict[str, Any]:
        return invoke(client, "sd_get_active_graph", {})

    @mcp.tool(
        name="sd_list_graph_nodes",
        description="List a bounded page of nodes from a structured graph reference.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_list_graph_nodes(
        graph: GraphRef,
        detail: Literal["summary", "full"] = "summary",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_list_graph_nodes",
            {
                "graph": graph.model_dump(mode="json"),
                "detail": detail,
                "offset": offset,
                "limit": limit,
            },
        )
