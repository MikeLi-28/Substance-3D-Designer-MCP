"""Runtime-typed simple node parameter tool."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.references import NodeRef
from substance_designer_mcp.models.responses import BridgeCaller, invoke

from .annotations import IDEMPOTENT_WRITE


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    @mcp.tool(
        name="sd_set_node_parameter",
        description=(
            "Set a supported simple parameter after reading and validating its runtime SD type."
        ),
        annotations=IDEMPOTENT_WRITE,
        structured_output=True,
    )
    def sd_set_node_parameter(node: NodeRef, property_id: str, value: Any) -> dict[str, Any]:
        return invoke(
            client,
            "sd_set_node_parameter",
            {
                "node": node.model_dump(mode="json"),
                "property_id": property_id,
                "value": value,
            },
            write=True,
        )
