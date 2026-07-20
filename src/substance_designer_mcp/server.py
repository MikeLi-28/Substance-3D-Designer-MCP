"""Official FastMCP stdio server assembly."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.bridge.client import BridgeClient
from substance_designer_mcp.models.responses import BridgeCaller
from substance_designer_mcp.tools import (
    authoring_tools,
    connection_tools,
    graph_tools,
    library_tools,
    node_tools,
    package_tools,
    parameter_tools,
    system_tools,
)


def build_server(client: BridgeCaller | None = None) -> FastMCP[Any]:
    """Build the complete v1.1.0 tool server without starting a transport."""

    bridge = client or BridgeClient()
    server: FastMCP[Any] = FastMCP(
        "substance-designer-mcp",
        instructions=(
            "Operate Adobe Substance 3D Designer through structured references and explicit "
            "runtime validation. Never guess node definitions, properties, or resource URLs."
        ),
        log_level="INFO",
    )
    system_tools.register(server, bridge)
    package_tools.register(server, bridge)
    graph_tools.register(server, bridge)
    node_tools.register(server, bridge)
    connection_tools.register(server, bridge)
    parameter_tools.register(server, bridge)
    library_tools.register(server, bridge)
    authoring_tools.register(server, bridge)
    # mcp 1.x builds argument models with Pydantic's default extra="ignore".
    # Tighten both runtime validation and the advertised schema for every tool.
    for tool_name in (
        "sd_ping",
        "sd_get_application_info",
        "sd_get_capabilities",
        "sd_list_packages",
        "sd_save_package",
        "sd_get_active_graph",
        "sd_list_graph_nodes",
        "sd_get_selection",
        "sd_get_node",
        "sd_list_node_properties",
        "sd_create_node",
        "sd_create_instance_node",
        "sd_move_nodes",
        "sd_delete_nodes",
        "sd_connect_nodes",
        "sd_disconnect_nodes",
        "sd_set_node_parameter",
        "sd_search_library",
        "sd_create_package",
        "sd_create_graph",
        "sd_list_node_definitions",
        "sd_get_graph_snapshot",
        "sd_open_graph",
        "sd_create_graph_output",
        "sd_save_package_as",
        "sd_validate_graph_patch",
        "sd_apply_graph_patch",
        "sd_import_bitmap",
        "sd_export_package_sbsar",
    ):
        tool = server._tool_manager.get_tool(tool_name)
        if tool is None:  # pragma: no cover - registration invariant
            raise RuntimeError(f"Tool registration failed: {tool_name}")
        model = tool.fn_metadata.arg_model
        model.model_config = {**model.model_config, "extra": "forbid"}
        model.model_rebuild(force=True)
        tool.parameters = model.model_json_schema(by_alias=True)
    return server
