"""Selection, node inspection, and validated node mutation tools."""

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.references import GraphRef, LibraryResourceRef, NodeRef
from substance_designer_mcp.models.requests import MoveSpec
from substance_designer_mcp.models.responses import BridgeCaller, invoke

from .annotations import DESTRUCTIVE, IDEMPOTENT_WRITE, READ_ONLY, WRITE


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    @mcp.tool(
        name="sd_get_selection",
        description="Read the current graph node selection with a bounded result size.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_get_selection(
        detail: Literal["summary", "full"] = "summary", limit: int = 100
    ) -> dict[str, Any]:
        return invoke(client, "sd_get_selection", {"detail": detail, "limit": limit})

    @mcp.tool(
        name="sd_get_node",
        description="Read one node by a structured current-session node reference.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_get_node(node: NodeRef, detail: Literal["summary", "full"] = "full") -> dict[str, Any]:
        return invoke(
            client,
            "sd_get_node",
            {"node": node.model_dump(mode="json"), "detail": detail},
        )

    @mcp.tool(
        name="sd_list_node_properties",
        description=(
            "List runtime input and output properties, types, values, and connection state."
        ),
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_list_node_properties(node: NodeRef) -> dict[str, Any]:
        return invoke(client, "sd_list_node_properties", {"node": node.model_dump(mode="json")})

    @mcp.tool(
        name="sd_create_node",
        description=(
            "Create one verified atomic node at an explicit position without auto-connecting it."
        ),
        annotations=WRITE,
        structured_output=True,
    )
    def sd_create_node(
        graph: GraphRef, definition_id: str, position: tuple[float, float]
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_create_node",
            {
                "graph": graph.model_dump(mode="json"),
                "definition_id": definition_id,
                "position": [float(position[0]), float(position[1])],
            },
            write=True,
        )

    @mcp.tool(
        name="sd_create_instance_node",
        description="Create one instance from a resource returned by sd_search_library.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_create_instance_node(
        graph: GraphRef, resource: LibraryResourceRef, position: tuple[float, float]
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_create_instance_node",
            {
                "graph": graph.model_dump(mode="json"),
                "resource": resource.model_dump(mode="json"),
                "position": [float(position[0]), float(position[1])],
            },
            write=True,
        )

    @mcp.tool(
        name="sd_move_nodes",
        description="Move one to one hundred explicitly identified nodes to finite coordinates.",
        annotations=IDEMPOTENT_WRITE,
        structured_output=True,
    )
    def sd_move_nodes(graph: GraphRef, moves: list[MoveSpec]) -> dict[str, Any]:
        return invoke(
            client,
            "sd_move_nodes",
            {
                "graph": graph.model_dump(mode="json"),
                "moves": [move.model_dump(mode="json") for move in moves],
            },
            write=True,
        )

    @mcp.tool(
        name="sd_delete_nodes",
        description="Delete explicit nodes from one graph only when confirm is true.",
        annotations=DESTRUCTIVE,
        structured_output=True,
    )
    def sd_delete_nodes(
        graph: GraphRef, node_identifiers: list[str], confirm: bool
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_delete_nodes",
            {
                "graph": graph.model_dump(mode="json"),
                "node_identifiers": node_identifiers,
                "confirm": confirm,
            },
            write=True,
        )
